from anthropic import AnthropicVertex

LOCATION="europe-west1" # or "us-east5"

client = AnthropicVertex(region=LOCATION, project_id="core-field-430709-r8")

message = client.messages.create(
  max_tokens=1024,
  messages=[
    {
      "role": "user",
      "content": "아아아아아아아.ㅋㅋㅋㅋ",
    }
  ],
  model="claude-3-5-sonnet@20240620",
)
print(message.model_dump_json(indent=2))