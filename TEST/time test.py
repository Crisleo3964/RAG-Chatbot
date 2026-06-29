from ollama import chat
import time

start = time.time()

chat(
    model="qwen3:1.7b",
    messages=[{"role":"user","content":"What is FastAPI?"}]
)

print(time.time() - start)