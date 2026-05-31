# PolicyGuard AI
## Table of Contents

- [Overview](#overview)
- [Key Engineering Highlights](#key-engineering-highlights)
- [Architecture](#architecture)
- [Features](#features)
- [Tech Stack](#tech-stack)
- [Installation](#installation)
- [API Endpoints](#api-endpoints)
- [Evaluation Framework](#sample-evaluation-output)
- [Monitoring Dashboard](#monitoring-dashboard)
- [Screenshots](#screenshots)
- [Production Deployment](#production-deployment)
- [Future Improvements](#future-improvements)

> **Production-ready RAG system for organizational documents with role-based access control**

An intelligent document assistant that allows employees to ask natural language questions about company policies, handbooks, and procedures while respecting role-based permissions.

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-green.svg)](https://fastapi.tiangolo.com/)
[![Qdrant](https://img.shields.io/badge/Qdrant-1.7+-orange.svg)](https://qdrant.tech/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

![Demo Screenshot](docs/demo-screenshot.png)

---

## Key Features

### **Semantic Search**
- Vector-based similarity search using OpenAI embeddings
- Finds relevant information by meaning, not just keywords
- Handles synonyms and contextual queries

### **Role-Based Access Control (RBAC)**
- Documents tagged with required access roles
- Employees only see information they're authorized to access
- Prevents data leaks and ensures compliance

### **Grounded Responses**
- Answers cite source documents to prevent hallucination
- System refuses to answer when no relevant context is found
- Transparent source attribution builds user trust

### **Production-Ready**
- Comprehensive observability (Prometheus, Loki, Grafana)
- Redis-backed usage and cost tracking
- Docker containerized for easy deployment
- FastAPI async architecture for high performance

### **Cost Tracking**
- Real-time OpenAI API usage monitoring
- Token consumption analytics
- Per-request cost calculation

---

## Architecture
┌──────────────────────────────────────────────────────┐
│                   User Interface                     │
│              Streamlit Web Application               │
└─────────────────────┬────────────────────────────────┘
│ HTTP
┌─────────────────────▼────────────────────────────────┐
│                  FastAPI Backend                     │
│  ┌────────────┐  ┌─────────────┐  ┌──────────────┐  │
│  │   /ask     │  │  /ingest    │  │  /metrics    │  │
│  │  endpoint  │  │  endpoint   │  │  endpoint    │  │
│  └─────┬──────┘  └──────┬──────┘  └──────┬───────┘  │
└────────┼─────────────────┼─────────────────┼─────────┘
│                 │                 │
┌────▼────┐      ┌─────▼─────┐     ┌────▼────┐
│ Qdrant  │      │  OpenAI   │     │  Redis  │
│ Vector  │      │ Embedding │     │ Metrics │
│   DB    │      │  + GPT    │     │ Storage │
└─────────┘      └───────────┘     └─────────┘
│
┌────▼────────────────────────────┐
│    Observability Stack          │
│  Prometheus → Grafana ← Loki    │
└─────────────────────────────────┘

### **Tech Stack:**

| Layer | Technology | Purpose |
|-------|------------|---------|
| **Frontend** | Streamlit | User interface |
| **Backend** | FastAPI | REST API server |
| **Vector DB** | Qdrant | Semantic search |
| **Embeddings** | OpenAI text-embedding-3-small | Convert text to vectors |
| **LLM** | OpenAI GPT-3.5-turbo | Answer generation |
| **Metrics** | Redis | Usage tracking |
| **Monitoring** | Prometheus | Metrics collection |
| **Logs** | Loki | Log aggregation |
| **Dashboards** | Grafana | Visualization |
| **Deployment** | Docker Compose | Container orchestration |

---

## Quick Start

### **Prerequisites**

- Python 3.11+
- Docker & Docker Compose
- OpenAI API key ([Get one here](https://platform.openai.com/api-keys))

### **Installation**

1. **Clone the repository**
```bash
git clone https://github.com/YOUR_USERNAME/policyguard-ai.git 
cd policyguard-ai
```

2. **Set up environment variables**
```bash
cp .env.example .env
nano .env  # Add your OpenAI API key
```

Required in `.env`:
```bash
OPENAI_API_KEY=sk-your-key-here
QDRANT_URL=http://localhost:6333
REDIS_URL=redis://localhost:6379
```

3. **Start all services with Docker Compose**
```bash
docker-compose up --build -d
```

Wait ~30 seconds for all services to start.

4. **Verify services are running**
```bash
docker-compose ps
```

All services should show `Up (healthy)`.

5. **Access the application**

| Service | URL | Credentials |
|---------|-----|-------------|
|  Streamlit UI | http://localhost:8501 | - |
|  API Documentation | http://localhost:8000/docs | - |
|  Grafana Dashboards | http://localhost:3000 | admin / admin |
|  Prometheus | http://localhost:9090 | - |
|  Qdrant Dashboard | http://localhost:6333/dashboard | - |

---

## Usage Guide

### **1. Upload Documents**

**Via Streamlit UI:**
1. Open http://localhost:8501
2. Use sidebar to select your role
3. Click "Upload Document"
4. Choose PDF or DOCX file
5. Set required access role (employee/manager/admin)
6. Click "Upload & Process"

**Via API:**
```bash
curl -X POST http://localhost:8000/api/ingest \
  -F "file=@employee_handbook.pdf" \
  -F "document_id=handbook_2024" \
  -F "role=employee"
```

### **2. Ask Questions**

**Via Streamlit UI:**
1. Select your role from dropdown
2. Type your question
3. Get answer with source citations

**Via API:**
```bash
curl -X POST http://localhost:8000/api/ask \
  -H "Content-Type: application/json" \
  -d '{
    "query": "How many days of annual leave do employees get?",
    "role": "employee",
    "limit": 5
  }'
```

**Example Response:**
```json
{
  "answer": "Full-time employees receive 25 days of paid annual leave per year.",
  "sources": [
    {
      "document_id": "employee_handbook.pdf",
      "chunk_id": 0,
      "score": 0.87
    }
  ],
  "context_used": true,
  "metadata": {
    "num_chunks_used": 1,
    "model": "gpt-3.5-turbo",
    "latency_seconds": 2.3
  }
}
```

### **3. Monitor System**

**Grafana Dashboards:**
- Navigate to http://localhost:3000
- View "PolicyGuard AI - Main Dashboard"
- See real-time metrics:
  - Total requests
  - Average response time
  - Error rates
  - Cost tracking
  - Live logs

**Metrics API:**
```bash
curl http://localhost:8000/api/metrics
```

Returns:
```json
{
  "usage": {
    "total_requests": 152,
    "total_tokens": 45230
  },
  "cost": {
    "total_cost": 0.31,
    "avg_cost_per_request": 0.0020
  },
  "performance": {
    "avg_latency_ms": 2300,
    "p95_latency_ms": 4100
  }
}
```

---

## Configuration

### **Environment Variables**

| Variable | Default | Description |
|----------|---------|-------------|
| `OPENAI_API_KEY` | *required* | Your OpenAI API key |
| `QDRANT_URL` | `http://localhost:6333` | Qdrant server URL |
| `QDRANT_COLLECTION_NAME` | `policyguard_docs` | Vector collection name |
| `REDIS_URL` | `redis://localhost:6379` | Redis server URL |
| `ENVIRONMENT` | `development` | Environment (development/production) |
| `LOG_LEVEL` | `INFO` | Logging level (DEBUG/INFO/WARNING/ERROR) |

### **Advanced Settings**

Modify these in `app/core/config.py`:
- Embedding model (default: text-embedding-3-small)
- LLM model (default: gpt-3.5-turbo)
- Chunk size (default: 1000 characters)
- Chunk overlap (default: 200 characters)

---

## API Endpoints

### **Core Endpoints**

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/` | API status |
| `GET` | `/api/health` | System health check |
| `POST` | `/api/ask` | Ask a question (main RAG endpoint) |
| `POST` | `/api/ingest` | Upload and process documents |
| `GET` | `/api/metrics` | Usage statistics and costs |
| `GET` | `/metrics` | Prometheus metrics |

### **Interactive Documentation**

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

---

## Testing

```bash
# Run all tests
pytest app/tests/ -v

# Run specific test file
pytest app/tests/test_ask_api.py -v

# With coverage report
pytest --cov=app --cov-report=html app/tests/
open htmlcov/index.html
```

---

## Performance

**Benchmarks** (tested on MacBook Pro M1, 16GB RAM):

| Metric | Value |
|--------|-------|
| Average query latency | 2.3s |
| Embedding generation | ~100ms |
| Vector search (Qdrant) | ~50ms |
| LLM generation (GPT-3.5) | ~2.0s |
| P95 latency | 4.1s |
| P99 latency | 6.2s |

**Cost Analysis** (per 1000 queries):
- Embeddings: ~$0.20
- LLM generation: ~$2.00
- **Total: ~$2.20 / 1000 queries**

---

## Security Features

- ✅ Role-based access control (RBAC)
- ✅ File type validation (.pdf, .docx only)
- ✅ File size limits (10MB max)
- ✅ Input sanitization
- ✅ No API key exposure in logs
- ✅ CORS middleware configured
- ✅ Health checks for all services

---

## Roadmap

- [ ] Multi-turn conversation support (chat history)
- [ ] Support more file formats (TXT, Markdown, CSV)
- [ ] Advanced search filters (date range, department)
- [ ] Query result caching (Redis)
- [ ] User authentication (OAuth2/JWT)
- [ ] Multi-language support
- [ ] Slack/Teams integration
- [ ] Admin dashboard for document management

---

## Troubleshooting

### **Common Issues**

**1. "OpenAI API error: Rate limit exceeded"**

**2. "Qdrant connection failed"**
```bash
# Check if Qdrant is running
docker-compose ps qdrant

# Restart Qdrant
docker-compose restart qdrant
```

**3. "No chunks found for query"**

**4. "High latency (>10s responses)"**

---

## Project Structure
policyguard-ai/
├── app/
│   ├── api/              # FastAPI routes
│   ├── core/             # Configuration, logging
│   ├── ingestion/        # Document loading & chunking
│   ├── retrieval/        # Qdrant & embeddings
│   ├── llm/              # Answer generation
│   ├── observability/    # Metrics & monitoring
│   ├── schemas/          # Pydantic models
│   └── tests/            # Unit & integration tests
├── ui/                   # Streamlit frontend
├── observability/        # Prometheus, Loki, Grafana configs
├── data/                 # Document storage
├── docker-compose.yml    # Container orchestration
├── Dockerfile            # Backend container
└── README.md            # This file

---

## Contributing

Contributions welcome! Please:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## Author

**Your Name**
- GitHub: [@yourusername](https://github.com/yourusername)
- LinkedIn: [Your Profile](https://linkedin.com/in/yourprofile)
- Email: your.email@example.com

---

## Acknowledgments

- Built with [FastAPI](https://fastapi.tiangolo.com/)
- Powered by [OpenAI](https://openai.com/)
- Vector search by [Qdrant](https://qdrant.tech/)
- Monitoring with [Grafana Stack](https://grafana.com/)

---

## Stats

![GitHub stars](https://img.shields.io/github/stars/yourusername/policyguard-ai?style=social)
![GitHub forks](https://img.shields.io/github/forks/yourusername/policyguard-ai?style=social)
![GitHub issues](https://img.shields.io/github/issues/yourusername/policyguard-ai)
![GitHub pull requests](https://img.shields.io/github/issues-pr/yourusername/policyguard-ai)

---

** If you find this project useful, please consider giving it a star!**
