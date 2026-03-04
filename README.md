# agent-p

A multi-service AI agent platform built around **n8n** as the workflow orchestrator, deployed on [Zeabur](https://zeabur.com). n8n is deployed via Zeabur's built-in template. Custom services are independently Dockerized and integrate with n8n via webhook triggers or the n8n API.

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────┐
│                   Zeabur Project                     │
│                                                     │
│  ┌──────────────┐     webhook / API                 │
│  │  n8n (main)  │◄────────────────────┐             │
│  │  [template]  │                     │             │
│  │  port 5678   │                     │             │
│  └──────┬───────┘                     │             │
│         │ HTTP Request node           │             │
│         ▼                             │             │
│  ┌──────────────┐   ┌──────────────┐  │             │
│  │    ffmpeg    │   │ map-to-poster│──┘             │
│  │ (media proc) │   │ (image gen)  │                │
│  └──────────────┘   └──────────────┘                │
└─────────────────────────────────────────────────────┘
```

Services communicate within the same Zeabur project using **private networking** (e.g. `http://ffmpeg.zeabur.internal:3000`), so they are never exposed publicly.

---

## Services

| Service | Description | Type |
|---------|-------------|------|
| `n8n` | Main workflow orchestrator | Zeabur template |
| `ffmpeg` | Media processing (video/audio conversion, thumbnail extraction, etc.) | Custom Dockerfile |
| `map-to-poster` | Render map tiles or geo data into poster images | Custom Dockerfile |
| *(add more)* | Flow-specific services | Custom Dockerfile |

Custom services live under `services/<name>/` with their own `Dockerfile` and `.env.example`.

---

## Project Structure

```
agent-p/
├── services/
│   ├── ffmpeg/
│   │   ├── Dockerfile
│   │   └── .env.example
│   └── map-to-poster/
│       ├── Dockerfile
│       └── .env.example
├── openspec/          # Spec-driven development docs
├── archives/          # Exported n8n workflow JSONs
└── README.md
```

---

## Deploying on Zeabur

### 1. Create a Zeabur Project

Go to [zeabur.com](https://zeabur.com) → **New Project**.

### 2. Deploy n8n via Template

Inside the project → **Add Service** → **Marketplace** → search **n8n** → Deploy.  
In the n8n service → **Networking** tab → generate a public domain so external webhooks can reach it.

### 3. Deploy Custom Services

For each service under `services/<name>/`:

1. Add a new service → **Deploy from source** → select this repo
2. Set the **root directory** to `services/<name>/`
3. Zeabur auto-detects the `Dockerfile` and builds it
4. Fill in environment variables from `.env.example` in the **Variables** tab

---

## Importing Workflows

Upload exported JSONs from `archives/` via **n8n UI → Import from file**.

---

## Inter-Service Integration

All services in the same Zeabur project share a **private network**. Use internal hostnames to call services without exposing them to the internet.

### Calling a Custom Service from n8n

Use the **HTTP Request** node in n8n with the internal hostname:

```
http://ffmpeg.zeabur.internal:3000/convert
http://map-to-poster.zeabur.internal:8080/render
```

### Calling n8n from a Custom Service

#### Option A — Webhook Trigger

```bash
curl -X POST http://n8n.zeabur.internal:5678/webhook/<your-path> \
  -H "Content-Type: application/json" \
  -d '{"key": "value"}'
```

#### Option B — n8n REST API

```bash
# List workflows
curl http://n8n.zeabur.internal:5678/api/v1/workflows \
  -H "X-N8N-API-KEY: <your-api-key>"

# Execute a workflow by ID
curl -X POST http://n8n.zeabur.internal:5678/api/v1/workflows/<id>/execute \
  -H "X-N8N-API-KEY: <your-api-key>" \
  -H "Content-Type: application/json" \
  -d '{"runData": {}}'
```

Generate an API key in n8n: **Settings → API → Create API Key**.

### Environment Variable Convention

Custom services that call n8n should declare these in their `.env.example`:

```env
N8N_INTERNAL_URL=http://n8n.zeabur.internal:5678
N8N_API_KEY=your-api-key
```

---

## Adding a New Service

1. Create `services/<name>/Dockerfile`.
2. Add `services/<name>/.env.example` with required variables.
3. Deploy on Zeabur following the steps in [Deploy Custom Services](#3-deploy-custom-services).
4. Add `N8N_INTERNAL_URL` / `N8N_API_KEY` if the service needs to call n8n.
5. Register it in the **Services** table in this README.

---

## Local Development

To test a custom service locally:

```bash
docker build -t my-service services/<name>/
docker run -p 3000:3000 --env-file services/<name>/.env my-service
```

---

## References

- [n8n Docs](https://docs.n8n.io)
- [n8n REST API](https://docs.n8n.io/api/)
- [Zeabur Docs](https://zeabur.com/docs)
- [Zeabur Private Networking](https://zeabur.com/docs/deploy/private-networking)
