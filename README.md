# Claire

Claire is a personal finance assistant that helps users understand spending, track goals, identify subscriptions, and chat for financial insights.

## Team members

- Irfan Naqieb
- Wan Adzhar Faiq Adzlan

## Problem statement

Personal finance data is fragmented across bank transactions and uploaded documents, making it time-consuming to understand cash flow, detect recurring subscriptions, and turn raw data into actionable insights. Not everyone can afford a dedicated wealth manager, but everyone can access their own financial statements and benefit from an automated assessment that provides similar clarity and guidance.

## Solution overview

Claire provides:

- A web dashboard to explore transactions, subscriptions, goals, and cash flow visualizations.
- A backend API that ingests transactions/uploads, stores them, and produces insights.
- An AI-powered chat/insights layer that can summarize financial activity and suggest actions. Talk to your financial statements and plan.

## How it works (high level)

1. User uploads a statement or transaction export.
2. Backend extracts and normalizes transactions.
3. The system computes derived signals (categories, subscriptions, aggregates).
4. Insights are generated and stored.
5. The dashboard and chat layer query the same underlying data for consistent outputs.

# Who this is for

- Individuals who want a clearer view of spending, subscriptions, and cash flow using statements they already have, and who are looking to improve their overall financial health and achieve personal financial goals.

## Tech stack used

Web: Next.js + shadcn/ui
Backend: FastAPI (Dockerized)
Database: Postgres (pgvector for semantic search/embedding use cases)
Object storage: MinIO (S3-compatible) in dev; S3/R2-compatible in production
Auth: Clerk (JWT)
AI: OpenAI models for extraction + chat/insights

## Setup instructions

### Prerequisites

- Docker Desktop (recommended for running everything)
- (Optional) Node.js + npm (if running the web app outside Docker)
- (Optional) Python 3.13+ (if running the backend outside Docker)
- OpenAI API Key
- Clerk API Key (For Auth)

### 1) Clone the repository

```bash
git clone https://github.com/irfannaqieb/claire.git
cd claire
```

### 2) Create a `.env` file

This project uses a root `.env` file (loaded by Docker Compose and by the backend settings). Create a `.env` in the repository root.

## Environment variables

Set these variables in your root `.env` before running locally.

### Web (Next.js)

- `NEXT_PUBLIC_API_BASE_URL` (example: `http://localhost:8000`)
- `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY`
- `CLERK_SECRET_KEY`

### Backend (FastAPI)

- `BACKEND_PROJECT_NAME` (example: `Claire API`)
- `BACKEND_API_V1_STR` (example: `/api/v1`)
- `BACKEND_API_VERSION` (example: `0.1.0`)
- `BACKEND_API_ENVIRONMENT` (example: `development`)
- `BACKEND_API_DESCRIPTION`
- `OPENAI_API_KEY`
- `LOG_LEVEL` (example: `INFO`)

### Postgres

- `POSTGRES_HOST` (Docker Compose: `db`, running locally outside Docker: `localhost`)
- `POSTGRES_PORT` (example: `5432`)
- `POSTGRES_USER`
- `POSTGRES_PASSWORD`
- `POSTGRES_DB`
- `POSTGRES_POOL_SIZE` (optional, example: `10`)
- `POSTGRES_MAX_OVERFLOW` (optional, example: `5`)

### MinIO (S3-compatible)

- `MINIO_ENDPOINT` (Docker Compose: `minio:9000`, running locally outside Docker: `localhost:9000`)
- `MINIO_SECURE` (example: `0` for http)
- `MINIO_ROOT_USER`
- `MINIO_ROOT_PASSWORD`
- `MINIO_ACCESS_KEY`
- `MINIO_SECRET_KEY`
- `MINIO_BUCKET_NAME`

### Clerk (Auth)

- `CLERK_SECRET_KEY`
- `CLERK_PUBLISHABLE_KEY`
- `CLERK_JWKS_URL`

### Minimal `.env` example

```bash
# Web
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=pk_test_...
CLERK_SECRET_KEY=sk_test_...

# Backend
BACKEND_PROJECT_NAME=Claire API
BACKEND_API_V1_STR=/api/v1
BACKEND_API_VERSION=0.1.0
BACKEND_API_ENVIRONMENT=development
BACKEND_API_DESCRIPTION=Claire API
OPENAI_API_KEY=...
LOG_LEVEL=INFO

# Postgres
POSTGRES_HOST=db
POSTGRES_PORT=5432
POSTGRES_USER=claire
POSTGRES_PASSWORD=claire
POSTGRES_DB=claire
POSTGRES_POOL_SIZE=10
POSTGRES_MAX_OVERFLOW=5

# MinIO
MINIO_ENDPOINT=minio:9000
MINIO_SECURE=0
MINIO_ROOT_USER=admin
MINIO_ROOT_PASSWORD=admin123
MINIO_ACCESS_KEY=minio-access
MINIO_SECRET_KEY=minio-secret
MINIO_BUCKET_NAME=uploads

# Clerk (all of this is available from clerk dashboard)
CLERK_JWKS_URL=https://<your-clerk-domain>/.well-known/jwks.json
CLERK_SECRET_KEY=sk_
CLERK_PUBLISHABLE_KEY=pk_
```

## Step-by-step guide: run the project locally

### Option A (recommended): Run everything with Docker Compose

1. Ensure Docker Desktop is running.

2. From the repo root, start the stack:

```bash
docker compose --env-file .env up --build
```

3. Open the services:

- Web app: http://localhost:3000
- Backend API docs (Swagger): http://localhost:8000/docs
- MinIO S3 API: http://localhost:9000
- MinIO Console: http://localhost:9001 (username: `MINIO_ROOT_USER`, password: `MINIO_ROOT_PASSWORD`)

4. Stop everything:

```bash
docker compose down
```

5. (Optional) Remove volumes to reset state:

```bash
docker compose down -v
```

### Run a single service outside Docker

If you'd like to work on/contribute code to a particular service, comment out the relevant service(s) in `docker-compose.yaml` and run the rest via Docker. For example, to run the backend locally while Postgres + MinIO remain in Docker:

1. Start dependencies:

```bash
docker compose --env-file .env up --build db minio createbuckets
```

2. In another terminal, run the backend locally (ensure your `.env` values match local networking):

- Set `POSTGRES_HOST=localhost`
- Set `MINIO_ENDPOINT=localhost:9000`

Then run:

```bash
cd apps/backend
python -m main
```
