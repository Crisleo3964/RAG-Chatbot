from __future__ import annotations

import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from groq import Groq

api_key = os.getenv("GROQ_API_KEY", "")
if not api_key:
    print("ERROR: GROQ_API_KEY environment variable is not set.")
    sys.exit(1)

model = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
temperature = float(os.getenv("GROQ_TEMPERATURE", "0.3"))
max_tokens = int(os.getenv("GROQ_MAX_TOKENS", "2048"))

client = Groq(api_key=api_key)

prompt = "What is the capital of France? Answer in one sentence."

print(f"Model: {model}")
print(f"Temperature: {temperature}")
print(f"Max tokens: {max_tokens}")
print(f"Prompt: {prompt}")
print()

t0 = time.perf_counter()
response = client.chat.completions.create(
    model=model,
    messages=[{"role": "user", "content": prompt}],
    temperature=temperature,
    max_tokens=max_tokens,
)
elapsed = time.perf_counter() - t0

print(f"Response time: {elapsed:.2f}s")
print()
print("--- Generated Answer ---")
print(response.choices[0].message.content)
print("---")
