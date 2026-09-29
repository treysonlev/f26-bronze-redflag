import os
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

# CS department uses openai API
client = OpenAI(
    base_url=os.getenv("LLM_API_URL"),
    api_key=os.getenv("LLM_API_KEY"),
)

# Bulk of the work, uses model names and put content in here
response = client.chat.completions.create(
    model="qwen3-8-flash-next",
    messages=[
        {"role": "system", "content": "You exist"},
        {"role": "user", "content": "Say hi and give a brief description of Old Dominion University"},
    ],
    temperature=0.7,
    max_tokens=300,
)

print(response.choices[0].message.content)
