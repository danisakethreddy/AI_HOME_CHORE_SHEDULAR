import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("XAI_API_KEY")
client = OpenAI(
    api_key=API_KEY,
    base_url="https://api.x.ai/v1",
)

models_to_test = ["grok-2", "grok-2-latest", "grok-beta", "grok-flash", "grok-3"]

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
