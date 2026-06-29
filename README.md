# RAG Chatbot

A full-stack Retrieval-Augmented Generation (RAG) chatbot that lets users upload PDF documents, ask questions, and receive AI-generated answers with source citations.

**LLM:** Groq API (`llama-3.3-70b-versatile`) | **Embeddings:** Ollama (`nomic-embed-text`) | **Vector DB:** ChromaDB | **Backend:** FastAPI | **Frontend:** React + TypeScript + Vite + Tailwind CSS

## Architecture

```
┌──────────────┐     HTTP      ┌──────────────────┐     RabbitMQ     ┌──────────────────┐
│   Frontend   │ ────────────> │   FastAPI App    │ ───────────────> │ Ingestion Worker │
│ (React/Vite) │ <──────────── │ (main.py)        │                  │ (async PDF proc) │
└──────────────┘               │                  │                  └──────────────────┘
                               │  ┌────────────┐  │
                               │  │ ChromaDB   │  │
                               │  │ (vectors)  │  │
                               │  └────────────┘  │
                               │  ┌────────────┐  │
                               │  │ Ollama     │  │  (embeddings only)
                               │  └────────────┘  │
                               │  ┌────────────┐  │
                               │  │ Groq API   │  │  (LLM inference)
                               │  └────────────┘  │
                               └──────────────────┘
```

## Project Structure

```text
├── main.py                          # FastAPI app entry point (launches server + worker)
├── Dockerfile                       # Container build
├── docker-compose.yml               # RabbitMQ + app services
├── run.ps1                          # Local Windows launcher
├── rag-chatbot/
│   ├── src/
│   │   ├── api/
│   │   │   ├── routes/              # FastAPI route handlers (chat, ingest, auth, health)
│   │   │   ├── schemas/             # Pydantic request/response models
│   │   │   └── dependencies/        # DI containers (services, auth, stores)
│   │   ├── auth/                    # JWT auth, user registration, password hashing
│   │   ├── config/                  # Central settings (env vars + defaults)
│   │   ├── ingestion/               # PDF ingestion (text extraction, OCR, chunking)
│   │   ├── retrieval/               # Semantic search service
│   │   ├── llm/                     # Groq client, Ollama client, prompt builder
│   │   ├── services/                # High-level RAG orchestration
│   │   ├── storage/                 # ChromaDB, document status, chat store
│   │   ├── messaging/               # RabbitMQ publisher/consumer
│   │   ├── workers/                 # Async ingestion worker process
│   │   ├── models/                  # Dataclass schemas
│   │   └── utils/                   # Chunking helpers
│   ├── frontend/                    # React + TypeScript + Vite UI
│   ├── data/                        # Uploaded PDF files
│   ├── chroma_db/                   # Persistent vector store
│   ├── requirements.txt
│   └── README.md
```

## Features

- **PDF Ingestion** — Upload PDFs via UI or API; text extraction with OCR fallback (Tesseract)
- **RAG Chat** — Ask questions; answers include source document/page citations
- **Async Processing** — Document ingestion via RabbitMQ queue with fallback to inline processing
- **User Authentication** — JWT-based registration/login; admin user auto-created on first run
- **Session Management** — Multi-turn chat sessions with history
- **Per-User Isolation** — Documents and chat sessions scoped to authenticated users (admin sees all)
- **Dockerized** — One-command deployment with `docker-compose up`

## Prerequisites

- Python 3.11+
- Node.js 20+
- Ollama installed and running locally (for embeddings)
- Groq API key

### Required Ollama Models

```bash
ollama pull nomic-embed-text
```

## Setup

### Backend

```bash
# From the repository root
python -m venv rag-chatbot/.venv
rag-chatbot\.venv\Scripts\Activate.ps1   # Windows
# source rag-chatbot/.venv/bin/activate  # macOS/Linux

pip install -r rag-chatbot/requirements.txt
```

### Frontend

```bash
cd rag-chatbot/frontend
npm install
```

### Environment Variables

| Variable | Default | Description |
|---|---|---|
| `GROQ_API_KEY` | — | Groq API key (required) |
| `GROQ_MODEL` | `llama-3.3-70b-versatile` | Groq model |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama server URL |
| `RAG_AUTH_ENABLED` | `true` | Enable/disable authentication |
| `JWT_SECRET_KEY` | `change-me-in-...` | Secret for JWT tokens |
| `RABBITMQ_URL` | `amqp://guest:guest@localhost:5672/` | RabbitMQ connection string |
| `RAG_TOP_K` | `5` | Number of chunks to retrieve |
| `RAG_CHUNK_SIZE` | `1000` | Characters per chunk |
| `RAG_CHUNK_OVERLAP` | `200` | Overlap between consecutive chunks |

## Running the App

### Local Development

```bash
# Set your Groq API key
$env:GROQ_API_KEY = "gsk_your_key_here"

# Run directly
python main.py
```

Or use the provided launcher:

```bash
.\run.ps1
```

The server starts at `http://127.0.0.1:8000`.

### Frontend Dev Server

```bash
cd rag-chatbot/frontend
npm run dev
```

Frontend runs at `http://localhost:5173` (proxies API requests to port 8000).

### Docker

```bash
$env:GROQ_API_KEY = "gsk_your_key_here"
$env:JWT_SECRET_KEY = "your-secret-key-at-least-32-characters-long!!"

docker-compose up --build
```

## API Endpoints

| Method | Path | Description |
|---|---|---|
| `GET` | `/health` | Health check |
| `POST` | `/auth/register` | Register a new user |
| `POST` | `/auth/token` | Login (get JWT token) |
| `GET` | `/auth/me` | Current user info |
| `GET` | `/auth/users` | List users (admin only) |
| `POST` | `/auth/users` | Create user (admin only) |
| `POST` | `/ingest` | Upload a PDF for ingestion |
| `GET` | `/documents/{id}/status` | Get document ingestion status |
| `GET` | `/documents/{id}/file` | Download uploaded PDF |
| `GET` | `/api/documents` | List all documents |
| `POST` | `/documents/{id}/retry` | Retry failed ingestion |
| `DELETE` | `/documents/{id}` | Delete document |
| `POST` | `/chat` | Ask a question (with session support) |
| `GET` | `/chat/sessions` | List chat sessions |
| `GET` | `/chat/sessions/{id}` | Get session messages |
| `DELETE` | `/chat/sessions/{id}` | Delete a session |

### Chat Example

```json
POST /chat
Authorization: Bearer <token>
{
  "question": "What is the leave policy?",
  "session_id": null
}

Response:
{
  "answer": "Employees are entitled to 18 weeks of paid leave...",
  "sources": [
    { "document": "HR_Policy.pdf", "page": 12 }
  ],
  "session_id": "abc-123"
}
```

## Ingestion Pipeline

1. PDF uploaded → saved to `rag-chatbot/data/`
2. Published to RabbitMQ queue (or processed inline if RabbitMQ unavailable)
3. Worker extracts text via `pypdf` with OCR fallback via Tesseract
4. Text split into sentence-aware chunks (~1000 chars, 200 overlap)
5. Embeddings generated via `nomic-embed-text` (Ollama)
6. Chunks + embeddings stored in ChromaDB with metadata (document name, page, user ID)

## Default Admin Credentials

On first run, an admin user is created automatically:
- **Email:** `admin@localhost`
- **Password:** Printed to the console at startup (random 12-char string)
