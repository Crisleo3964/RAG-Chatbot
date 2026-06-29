# Build stage
FROM python:3.11-slim as builder

WORKDIR /tmp/build

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY rag-chatbot/requirements.txt .
RUN pip install --upgrade pip setuptools wheel && \
    pip install --no-cache-dir --user -r requirements.txt


# Runtime stage
FROM python:3.11-slim

WORKDIR /app

# Copy Python packages from builder
COPY --from=builder /root/.local /root/.local
ENV PATH=/root/.local/bin:$PATH

# Install Tesseract OCR for page rendering
RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    && rm -rf /var/lib/apt/lists/*

# Copy application code
COPY main.py .
COPY rag-chatbot/src ./rag-chatbot/src
COPY rag-chatbot/data ./rag-chatbot/data
COPY rag-chatbot/frontend ./rag-chatbot/frontend

# Create directories for runtime data
RUN mkdir -p chroma_db data

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV RAG_AUTH_ENABLED=true
ENV GROQ_MODEL=llama-3.3-70b-versatile
ENV OLLAMA_BASE_URL=http://ollama:11434
ENV RABBITMQ_URL=amqp://guest:guest@rabbitmq:5672/

# Expose port
EXPOSE 8000

# Run the application using root main.py (which sets up PYTHONPATH)
CMD ["python", "main.py"]
