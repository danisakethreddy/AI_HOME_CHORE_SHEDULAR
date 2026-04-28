import os
from openai import OpenAI
from dotenv import load_dotenv

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(BASE_DIR, ".env"), override=True)

API_KEY = os.getenv("XAI_API_KEY")

if API_KEY and API_KEY.startswith("gsk_"):
    base_url = "https://api.groq.com/openai/v1"
    models_to_test = ["llama-3.3-70b-versatile", "llama-3.1-8b-instant"]
elif API_KEY:
    base_url = "https://api.x.ai/v1"
    models_to_test = ["grok-3", "grok-2-latest", "grok-2", "grok-beta", "grok-flash"]
else:
    base_url = "https://api.x.ai/v1"
    models_to_test = []

client = OpenAI(
    api_key=API_KEY,
    base_url=base_url,
)

for model in models_to_test:
    print(f"Testing {model}...")
    try:
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": "hi"}],
            max_tokens=1
        )
        print(f"Success with {model}!")
        break
    except Exception as e:
        print(f"Failed with {model}: {e}")
