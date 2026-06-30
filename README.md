# SupportMesh 🕸️

## Overview

SupportMesh is an AI-powered customer support operations platform that automates ticket processing using FastAPI, PostgreSQL, pgvector, Retrieval-Augmented Generation (RAG), Groq LLM, webhooks, and Docker.

The current MVP is designed primarily as an internal support operations dashboard and AI processing engine. It receives support tickets, retrieves customer context, searches a vectorized knowledge base, generates AI-assisted classifications and draft responses, stores results in PostgreSQL, triggers webhook notifications, and displays operational metrics through a live dashboard.

## Current Features

- AI-powered ticket processing
- Customer lookup from PostgreSQL
- Retrieval-Augmented Generation (RAG) over a knowledge base
- Ticket classification
- AI-generated draft responses
- Confidence scoring
- PostgreSQL storage
- Webhook notifications
- Analytics dashboard
- Dockerized deployment
- Synthetic seed data for demonstration

## Current Workflow

1. Ticket is submitted.
2. Customer information is retrieved.
3. Relevant knowledge base articles are retrieved using vector search.
4. Context is sent to the Groq LLM.
5. AI classifies the issue and drafts a response.
6. Results are stored in PostgreSQL.
7. Webhook notifications are sent.
8. Dashboard displays the processed ticket.

## Architecture

```text
Customer/Admin
      |
      v
FastAPI Backend
      |
      v
PostgreSQL + pgvector
      |
      v
Semantic Search (RAG)
      |
      v
Groq LLM
      |
      v
AI Classification & Draft Response
      |
      v
PostgreSQL
      |
      v
Dashboard + Webhooks
```

## Detailed Processing Flow

1. **Submit Ticket**: Submit a ticket specifying the customer's unique ID, a subject, the ticket body content, and a priority level.
2. **Customer Lookup**: The system queries PostgreSQL for the customer's account details and recent ticket logs.
3. **Vector Embedding**: The ticket details are vectorized using `sentence-transformers` (`all-MiniLM-L6-v2`) locally.
4. **RAG Context Retrieval**: The vector is searched against the `knowledge_base` using pgvector cosine-distance to retrieve the top 3 most relevant support articles.
5. **LLM Synthesis**: The ticket, customer history, and retrieved articles are compiled into a prompt and sent to Groq (`llama-3.3-70b-versatile`) using OpenAI-style tool calling.
6. **Structured Output**: The LLM returns a structured JSON object containing a classification, confidence score, status, and draft response.
7. **Database Saving**: The ticket is saved in PostgreSQL with a calculated processing latency timestamp.
8. **Webhook Notification**: An outbound HTTP POST webhook containing the complete ticket payload is triggered asynchronously in the background.
9. **Dashboard Live Update**: The operations dashboard fetches metrics and lists the new ticket.

## Project Scope

This repository currently implements the AI backend and support operations dashboard for an internal support team. It focuses on backend architecture, AI orchestration, RAG-based retrieval, database persistence, webhook integration, and operational visibility.

Customer authentication, customer registration, and customer-facing support workflows are intentionally outside the scope of the current MVP. Those features are planned as later product milestones rather than missing pieces of the present implementation.

## Why This Project

The objective of SupportMesh is to demonstrate enterprise AI engineering concepts in a practical backend system, including:

- API design
- Database engineering
- Vector search
- Retrieval-Augmented Generation (RAG)
- LLM orchestration
- Docker
- Webhooks
- Production backend architecture

SupportMesh is intended to showcase how these systems fit together in a realistic support operations workflow rather than to serve as a complete customer support SaaS product.

---

## Setup & Running with Docker (Recommended)

Running with Docker Compose is the easiest way to launch the application with all systems (PostgreSQL, pgvector, FastAPI) fully configured.

### 1. Configure the Environment
Create a `.env` file in the root directory:
```bash
cp .env.example .env
```
Edit the `.env` file to add your Groq API key:
```ini
GROQ_API_KEY=gsk_your_groq_key_here
```
> **Note**: If you don't have a Groq API key, the LLM service will automatically fall back to generating realistic mock responses using local heuristics and your retrieved RAG articles, allowing you to test the complete application end-to-end.

### 2. Build and Start the Application
Run the following command to start both services:
```bash
docker compose up --build
```
This builds the application container (caching the `all-MiniLM-L6-v2` transformer model for fast startup times) and spins up PostgreSQL with the pgvector extension enabled.

### 3. Seed the Database
In a new terminal window, seed the database with synthetic customers, articles, and sample tickets:
```bash
# Seed the knowledge base articles with vector embeddings
docker compose exec app python scripts/embed_knowledge.py

# Seed the customers and sample tickets
docker compose exec app python scripts/seed.py
```

### 4. Open the Operations Dashboard
Go to your browser and open:
**[http://localhost:8000/dashboard](http://localhost:8000/dashboard)**

---

## Local Setup (Without Docker)

If you prefer to run the application directly on your host machine:

### 1. Requirements
Ensure you have:
- Python 3.11+
- PostgreSQL instance running locally with the `vector` extension installed (`CREATE EXTENSION IF NOT EXISTS vector;` enabled).

### 2. Install Dependencies
Create a virtual environment and install packages:
```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 3. Configure local Environment
Create a `.env` file and set the DB host to `localhost`:
```ini
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/supportmesh
GROQ_API_KEY=gsk_your_groq_key_here
```

### 4. Run Seeding Scripts
```bash
python scripts/embed_knowledge.py
python scripts/seed.py
```

### 5. Start Dev Server
```bash
uvicorn app.main:app --reload --port 8000
```

---

## API Documentation

Interactive OpenAPI docs are available at **[http://localhost:8000/docs](http://localhost:8000/docs)**.

### Primary Endpoints
* **`GET /dashboard`**: HTML operations dashboard.
* **`GET /api/stats`**: Serves aggregates (latency, resolution rates, category breakdowns, recent tickets logs).
* **`POST /tickets`**: Submit a new ticket.
  - **Body**:
    ```json
    {
      "customer_id": "c1a6b0c2-5555-4abc-9999-d41a7708502f",
      "subject": "Billing issue",
      "body": "I got charged twice for my subscription this month. Please help.",
      "priority": "high"
    }
    ```
* **`GET /tickets`**: List all tickets.
* **`GET /tickets/{id}`**: Retrieve ticket by ID.
* **`POST /tickets/webhook-demo-endpoint`**: Local endpoint that logs delivered webhooks for verification.

---

## Roadmap (Planned Features)

The following roadmap describes future product milestones for expanding SupportMesh beyond the current internal operations MVP.

### Phase 2 — Customer Portal

- Customer registration
- Secure login using JWT authentication
- Customer dashboard
- Raise support tickets directly
- View ticket history
- View AI-generated responses
- Profile management

### Phase 3 — Admin Portal

- Customer management
- Ticket assignment
- Agent management
- Knowledge base management
- Ticket filtering and search
- Analytics improvements
- Role-based access control

### Phase 4 — AI Improvements

- Multi-turn conversations
- Conversation history
- Feedback loop for AI responses
- Escalation to human agents
- Better retrieval and reranking
- Multiple LLM provider support
- Streaming responses
- Background task processing

### Phase 5 — Production Features

- OAuth login
- Email notifications
- File attachments
- Redis caching
- Celery workers
- Monitoring and logging
- Kubernetes deployment
- CI/CD improvements
- Multi-tenant architecture
