from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from anthropic import AnthropicVertex
import markdown2
import json

app = FastAPI()
LOCATION = "europe-west1"  # or "us-east5"
client = AnthropicVertex(region=LOCATION, project_id="core-field-430709-r8")
sonnet = "claude-3-5-sonnet@20240620"
templates = Jinja2Templates(directory="templates")

# 전역 변수로 대화 세션을 저장
conversation_history = []

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request, "system_message": "system"})

@app.post("/chat/", response_class=HTMLResponse)
async def chat(request: Request, system_message: str = Form(...), user: str = Form(...)):
    global conversation_history

    # 새로운 사용자 메시지를 대화 기록에 추가
    conversation_history.append({"role": "user", "content": user})

    # 클로드 API 호출
    message = client.messages.create(
        model=sonnet,
        max_tokens=1000,
        temperature=0,
        system=system_message,
        messages=conversation_history
    )

    message_json = json.loads(message.model_dump_json(indent=2))
    message = message_json['content'][0]['text']

    # 응답 메시지를 대화 기록에 추가
    assistant_response = message
    conversation_history.append({"role": "assistant", "content": assistant_response})

    response_message = assistant_response + f'사용토큰 {message_json['usage']['input_tokens']}'
    response_message_md = markdown2.markdown(response_message, extras=["fenced-code-blocks"])
    
    return templates.TemplateResponse("index.html", {
        "request": request, 
        "response_message": response_message_md, 
        "system_message": system_message
    })
