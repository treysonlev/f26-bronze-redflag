# Functions for calling llm endpoint, and setting up model
import os

from dotenv import load_dotenv
from openai import OpenAI

# Make sure you've got your .env, and never ever commit it since it has
# a literal key for llm api.
load_dotenv()

# We can change the model at any time, qwen for now is pretty good.
DEFAULT_MODEL = os.getenv("LLM_MODEL", "qwen3-8-flash-next")


# Connect to the actual llm endpoint, it'll raise an error if it's not working
def get_client():
    api_url = os.getenv("LLM_API_URL")
    api_key = os.getenv("LLM_API_KEY")
    if not api_url or not api_key:
        raise RuntimeError(
            "LLM_API_URL/LLM_API_KEY not set, look at README"
        )
    return OpenAI(base_url=api_url, api_key=api_key)

# The system tells it what it's personality is.
# Temperature defines how creative the output is, 
# 0 is not creative 1 is very creative

# Max tokens defines how big the returned text can be,
# if you're running into issues with nothing coming back try
# increasing it

def chat(prompt, system="You exist", temperature=0.7, max_tokens=300):
    client = get_client() #connects to the endpoint
    response = client.chat.completions.create( #This is the actual prompt
        model=DEFAULT_MODEL,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": prompt},
        ],
        temperature=temperature,
        max_tokens=max_tokens,
    )
    return response.choices[0].message.content #Returns response from prompt
