# SupportMesh: AI-Assisted Support Ticket Triage Using Retrieval-Augmented Generation

A backend platform that processes customer support tickets end to end: it retrieves customer context, searches a vectorised knowledge base, and uses a large language model to classify each ticket and draft a grounded response. Results are persisted, pushed to external systems by webhook, and surfaced on a live operations dashboard.

---

## Table of Contents

1. [Overview](#overview)
2. [Motivation](#motivation)
3. [Problem Statement](#problem-statement)
4. [Key Features](#key-features)
5. [Architecture](#architecture)
6. [Processing Flow](#processing-flow)
7. [Tech Stack](#tech-stack)
8. [Repository Structure](#repository-structure)
9. [Setup](#setup)
10. [API Reference](#api-reference)
11. [Evaluation](#evaluation)
12. [Scope and Limitations](#scope-and-limitations)
13. [Roadmap](#roadmap)

---

## Overview

SupportMesh is an internal support-operations system and AI processing engine. A submitted ticket triggers a pipeline that looks up the customer in PostgreSQL, embeds the ticket text, retrieves the three most relevant knowledge-base articles with pgvector, and sends the combined context to a Groq-hosted LLM. The model returns a structured result containing a classification, a confidence score, a status, and a draft response. The ticket is stored with its processing latency, a webhook is dispatched in the background, and the dashboard updates.

## Motivation

This project was built to study how the components of a production AI backend fit together in one realistic workflow: API design, relational and vector storage, retrieval, LLM orchestration with structured output, asynchronous integration, and containerised deployment. Support triage was chosen because it needs all of them, and because its output (a draft reply) can be checked against a knowledge base and a customer's history.

## Problem Statement

Support teams spend significant time reading tickets, looking up the customer, searching internal documentation, and writing similar replies repeatedly. Responses drafted by an LLM alone are unreliable because the model does not know the company's policies or the customer's account.

SupportMesh addresses this by grounding every draft in two sources of truth: the customer's own record and ticket history, and retrieved knowledge-base articles. The output is a draft with a classification and confidence score for a human agent to review.

## Key Features

- Ticket ingestion through a REST API with customer ID, subject, body, and priority
- Customer lookup and recent ticket history from PostgreSQL
- Semantic retrieval over a knowledge base using pgvector cosine distance
- Local embedding with `all-MiniLM-L6-v2`, so ticket text is not sent to an embedding API
- LLM classification and draft generation through tool calling, returning structured JSON
- Confidence score and status for each processed ticket
- Processing latency recorded for every ticket
- Asynchronous outbound webhooks carrying the full ticket payload
- Live operations dashboard with aggregate metrics
- Docker Compose deployment and synthetic seed data
- Graceful fallback to heuristic mock responses when no API key is set, so the full pipeline can be run without external access

## Architecture

```text
Customer / Admin
      |
      v
FastAPI backend
      |
      v
PostgreSQL + pgvector  <---- customer records, ticket history, knowledge base
      |
      v
Semantic search (RAG)  ----> top-3 articles
      |
      v
Groq LLM (llama-3.3-70b-versatile)
      |
      v
Classification, confidence score, draft response
      |
      v
PostgreSQL  ----> Dashboard and webhooks
```

## Processing Flow

1. **Submit ticket.** The client submits a customer ID, subject, body, and priority.
2. **Customer lookup.** PostgreSQL returns the account details and recent tickets.
3. **Embedding.** The ticket text is embedded locally with `sentence-transformers` (`all-MiniLM-L6-v2`).
4. **Retrieval.** pgvector returns the top three knowledge-base articles by cosine distance.
5. **Generation.** The ticket, customer history, and articles are combined into a prompt and sent to Groq (`llama-3.3-70b-versatile`) with OpenAI-style tool calling.
6. **Structured output.** The model returns JSON with a classification, confidence score, status, and draft response.
7. **Persistence.** The ticket and result are saved with the measured processing latency.
8. **Webhook.** A background HTTP POST sends the complete ticket payload to the configured endpoint.
9. **Dashboard.** The operations dashboard fetches updated metrics and lists the new ticket.

## Tech Stack

| Layer | Technology |
|---|---|
| API framework | FastAPI |
| Database | PostgreSQL with pgvector |
| Embeddings | sentence-transformers, `all-MiniLM-L6-v2` |
| LLM | Groq, `llama-3.3-70b-versatile` |
| Async DB driver | asyncpg |
| Containerisation | Docker, Docker Compose |
| Language | Python 3.11+ |

## Repository Structure

```
.
├── app/
│   └── main.py              # FastAPI application entry point
├── scripts/
│   ├── embed_knowledge.py   # Embeds knowledge-base articles into pgvector
│   └── seed.py              # Seeds synthetic customers and sample tickets
├── docker-compose.yml       # Application and PostgreSQL (pgvector) services
├── Dockerfile
├── requirements.txt
└── .env.example
```

## Setup

### Option 1: Docker (recommended)

1. Create the environment file and add your Groq key:

   ```bash
   cp .env.example .env
   ```

   ```ini
   GROQ_API_KEY=gsk_your_groq_key_here
   ```

   Without a key, the LLM service falls back to heuristic mock responses built from the retrieved articles. This mode exercises the whole pipeline but does not produce real model output.

2. Build and start the services:

   ```bash
   docker compose up --build
   ```

3. In a second terminal, seed the database:

   ```bash
   docker compose exec app python scripts/embed_knowledge.py
   docker compose exec app python scripts/seed.py
   ```

4. Open the dashboard at `http://localhost:8000/dashboard`.

### Option 2: Local, without Docker

Requirements: Python 3.11 or later, and a local PostgreSQL instance with the `vector` extension (`CREATE EXTENSION IF NOT EXISTS vector;`).

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Create `.env`:

```ini
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/supportmesh
GROQ_API_KEY=gsk_your_groq_key_here
```

Seed and run:

```bash
python scripts/embed_knowledge.py
python scripts/seed.py
uvicorn app.main:app --reload --port 8000
```

## API Reference

Interactive OpenAPI documentation is served at `http://localhost:8000/docs`.

| Method | Endpoint | Description |
|---|---|---|
| GET | `/dashboard` | HTML operations dashboard |
| GET | `/api/stats` | Aggregates: latency, resolution rates, category breakdown, recent tickets |
| POST | `/tickets` | Submit and process a new ticket |
| GET | `/tickets` | List all tickets |
| GET | `/tickets/{id}` | Retrieve a ticket by ID |
| POST | `/tickets/webhook-demo-endpoint` | Local endpoint that logs delivered webhooks for verification |

Example request to `POST /tickets`:

```json
{
  "customer_id": "c1a6b0c2-5555-4abc-9999-d41a7708502f",
  "subject": "Billing issue",
  "body": "I got charged twice for my subscription this month. Please help.",
  "priority": "high"
}
```

## Evaluation

The system records processing latency for every ticket, and `/api/stats` reports latency, resolution rate, and category distribution. The following protocol is used to evaluate it:

| Aspect | Method |
|---|---|
| Latency | Mean and 95th percentile of the stored processing latency over the seeded ticket set, with retrieval and LLM time reported separately |
| Classification accuracy | Comparison of the model's category against a hand-labelled ticket set |
| Retrieval quality | Fraction of tickets where a relevant article appears in the top 3 |
| Draft quality | Manual grading of drafts as usable, needs edits, or incorrect |

Results are reported only for the live Groq model, not for the heuristic fallback mode.

## Scope and Limitations

- The current release is an internal operations tool. Customer registration, authentication, and customer-facing workflows are outside its scope and appear on the roadmap.
- The confidence score is produced by the model and has not been calibrated against actual correctness.
- Retrieval uses dense similarity only, with no reranking, and returns a fixed top three.
- Tickets are processed independently; there is no multi-turn conversation state.
- Webhook delivery runs in the background without a retry queue.
- The seeded data is synthetic and does not reflect real customer traffic.

## Roadmap

| Phase | Focus | Planned work |
|---|---|---|
| 2 | Customer portal | Registration, JWT login, ticket submission and history, profile management |
| 3 | Admin portal | Ticket assignment, agent and knowledge-base management, search and filtering, role-based access control |
| 4 | AI improvements | Multi-turn conversations, feedback loop, human escalation, reranking, multiple LLM providers, streaming, background processing |
| 5 | Production readiness | OAuth, email notifications, attachments, Redis caching, Celery workers, monitoring, Kubernetes, CI/CD, multi-tenancy |
