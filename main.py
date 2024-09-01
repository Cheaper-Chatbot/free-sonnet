from fastapi import FastAPI, HTTPException, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
from anthropic import AnthropicVertex
import json
import uuid
from database import User, Conversation, Message, get_db

app = FastAPI()
LOCATION = "europe-west1"
client = AnthropicVertex(region=LOCATION, project_id="core-field-430709-r8")
sonnet = "claude-3-5-sonnet@20240620"

# Pydantic models
class MessageCreate(BaseModel):
    system_msg: Optional[str] = None
    user_msg: str
    user_ip: str
    conv_id: str
    timestamp: str

class MessageResponse(BaseModel):
    output_msg: str
    conv_id: str
    timestamp: str
    msg_id: str
    token: int

class ConversationResponse(BaseModel):
    speaker: str
    msg_contents: str
    timestamp: str
    msg_id: str

class UserCreate(BaseModel):
    id: str
    pw: str

# Helper functions
def generate_id():
    return str(uuid.uuid4())

# API endpoints
@app.post("/messages", response_model=MessageResponse)
async def create_message(message: MessageCreate, db: Session = Depends(get_db)):
    # Claude API call
    claude_message = client.messages.create(
        model=sonnet,
        max_tokens=1000,
        temperature=0,
        system=message.system_msg or "You are a helpful assistant.",
        messages=[{"role": "user", "content": message.user_msg}]
    )

    message_json = json.loads(claude_message.model_dump_json(indent=2))
    output_msg = message_json['content'][0]['text']
    
    # Save user message
    user_msg = Message(
        id=generate_id(),
        conversation_id=message.conv_id,
        speaker="user",
        content=message.user_msg,
        timestamp=datetime.fromisoformat(message.timestamp)
    )
    db.add(user_msg)

    # Save assistant message
    assistant_msg = Message(
        id=generate_id(),
        conversation_id=message.conv_id,
        speaker="assistant",
        content=output_msg,
        timestamp=datetime.utcnow()
    )
    db.add(assistant_msg)
    db.commit()

    return MessageResponse(
        output_msg=output_msg,
        conv_id=message.conv_id,
        timestamp=assistant_msg.timestamp.isoformat(),
        msg_id=assistant_msg.id,
        token=message_json['usage']['input_tokens']
    )

@app.put("/messages", response_model=MessageResponse)
async def update_message(message: MessageCreate, db: Session = Depends(get_db)):
    # For simplicity, we're just creating a new message instead of updating
    return await create_message(message, db)

@app.get("/conversations/{user_id}/{conv_id}", response_model=List[ConversationResponse])
async def get_conversation(user_id: str, conv_id: str, db: Session = Depends(get_db)):
    messages = db.query(Message).filter(Message.conversation_id == conv_id).all()
    if not messages:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return [
        ConversationResponse(
            speaker=msg.speaker,
            msg_contents=msg.content,
            timestamp=msg.timestamp.isoformat(),
            msg_id=msg.id
        ) for msg in messages
    ]

@app.post("/conversations", response_model=str)
async def create_conversation(user_id: str, db: Session = Depends(get_db)):
    new_conv = Conversation(id=generate_id(), user_id=user_id)
    db.add(new_conv)
    db.commit()
    return new_conv.id

@app.delete("/conversations/{user_id}/{conv_id}")
async def delete_conversation(user_id: str, conv_id: str, db: Session = Depends(get_db)):
    conv = db.query(Conversation).filter(Conversation.id == conv_id, Conversation.user_id == user_id).first()
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    db.delete(conv)
    db.commit()
    return {"status": "success"}

@app.post("/users", response_model=bool)
async def create_user(user: UserCreate, db: Session = Depends(get_db)):
    existing_user = db.query(User).filter(User.id == user.id).first()
    if existing_user:
        return False
    new_user = User(id=user.id, password=user.pw)  # Note: In a real app, you should hash the password
    db.add(new_user)
    db.commit()
    return True

@app.patch("/users/{user_id}/permissions")
async def update_user_permissions(user_id: str, valid_key: str, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return {"status": "success"}