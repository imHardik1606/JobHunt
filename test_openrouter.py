import requests
import os
from dotenv import load_dotenv

load_dotenv()

key = os.getenv("OPENROUTER_API_KEY_1")

if not key:
    print("ERROR: OPENROUTER_API_KEY_1 not found in .env file")
    exit(1)

print(f"Key found: {key[:8]}...")

r = requests.post(
    "https://openrouter.ai/api/v1/chat/completions",
    headers={
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://github.com/imHardik1606/jobhunt",
        "X-Title": "JobHunt"
    },
    json={
        "model": "openrouter/free",
        "messages": [{"role": "user", "content": "Reply with just the word: working"}],
        "max_tokens": 10
    }
)

print(f"Status: {r.status_code}")

if r.status_code == 200:
    content = r.json()["choices"][0]["message"]["content"]
    print(f"Response: {content}")
    print("✓ OpenRouter is working correctly")
else:
    print(f"Error: {r.text}")