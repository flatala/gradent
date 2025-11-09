# Gradent Deployment Architecture

## System Architecture Diagram

```
                                    Internet
                                       │
                                       │
                            ┌──────────▼──────────┐
                            │   Ubuntu VM / VPS   │
                            │   (your-ip:80)      │
                            └──────────┬──────────┘
                                       │
                            ┌──────────▼──────────┐
                            │   Docker Network    │
                            │  gradent-network    │
                            └──────────┬──────────┘
                                       │
                    ┌──────────────────┴──────────────────┐
                    │                                      │
         ┌──────────▼──────────┐              ┌───────────▼──────────┐
         │   Frontend Service  │              │   Backend Service    │
         │                     │              │                      │
         │  Container:         │              │  Container:          │
         │  gradent-frontend   │              │  gradent-backend     │
         │                     │              │                      │
         │  Image:             │              │  Image:              │
         │  - Node 20 Alpine   │              │  - Python 3.11 slim  │
         │  - Nginx            │              │  - Poetry            │
         │                     │              │                      │
         │  Ports:             │              │  Ports:              │
         │  - 80 (HTTP)        │◄────Proxy────│  - 8000 (Internal)   │
         │  - 443 (HTTPS)      │   /api/*     │                      │
         │                     │              │                      │
         │  Serves:            │              │  Runs:               │
         │  - React App        │              │  - FastAPI           │
         │  - Static Assets    │              │  - LangGraph Agents  │
         │  - SPA Routing      │              │  - Workflows         │
         └─────────────────────┘              └───────────┬──────────┘
                                                           │
                                              ┌────────────┴────────────┐
                                              │                         │
                                    ┌─────────▼────────┐    ┌──────────▼─────────┐
                                    │   SQLite DB      │    │   Vector DB        │
                                    │                  │    │   (Chroma)         │
                                    │   Location:      │    │                    │
                                    │   /app/data/     │    │   Location:        │
                                    │                  │    │   /app/data/       │
                                    │   Contains:      │    │   vector_db/       │
                                    │   - Users        │    │                    │
                                    │   - Courses      │    │   Contains:        │
                                    │   - Assignments  │    │   - Course docs    │
                                    │   - Progress     │    │   - Resources      │
                                    │   - History      │    │   - Embeddings     │
                                    └──────────────────┘    └────────────────────┘
```

## Container Communication

```
┌─────────────────────────────────────────────────────────────────┐
│                        Docker Network                            │
│                      (gradent-network)                           │
│                                                                   │
│   ┌─────────────┐           Network           ┌─────────────┐   │
│   │  Frontend   │────────────────────────────▶│   Backend   │   │
│   │             │   http://backend:8000       │             │   │
│   │  (nginx)    │                             │  (uvicorn)  │   │
│   └─────────────┘                             └─────────────┘   │
│         │                                            │           │
│         │                                            │           │
│   Host Port 80                              Host Port 8000       │
│         │                                            │           │
└─────────┼────────────────────────────────────────────┼───────────┘
          │                                            │
          ▼                                            ▼
    User Browser                              Direct API Access
    http://vm-ip/                             http://vm-ip:8000/docs
```

## Data Flow

### User Request Flow

```
┌──────┐     ①      ┌─────────┐     ②      ┌─────────┐
│ User │────────────▶│ Nginx   │────────────▶│ FastAPI │
│      │  HTTP/80    │         │ /api/*     │         │
└──────┘             └─────────┘             └─────────┘
                          │                       │
                          │ ③ Static Files        │ ④ Process
                          │                       │
                          ▼                       ▼
                    ┌──────────┐           ┌──────────┐
                    │  React   │           │ LangGraph│
                    │  Assets  │           │  Agent   │
                    └──────────┘           └─────┬────┘
                                                  │
                                        ⑤ Query   │
                                                  ▼
                                          ┌───────────────┐
                                          │   Databases   │
                                          │ - SQLite      │
                                          │ - Vector DB   │
                                          └───────────────┘
```

### Volume Mounts

```
┌────────────────────────────────────────────────────────┐
│                    Host System                         │
│                    (Ubuntu VM)                         │
│                                                         │
│  /home/user/gradent/                                   │
│  ├── data/                  ◄────┐                    │
│  │   ├── study_assistant.db       │ Volume Mount      │
│  │   └── vector_db/               │                    │
│  │       └── chroma.sqlite3        │                    │
│  │                                 │                    │
│  ├── logs/                  ◄────┤                    │
│  │   └── app.log                   │                    │
│  │                                 │                    │
│  ├── uploads/               ◄────┤                    │
│  │   └── user_files/               │                    │
│  │                                 │                    │
│  └── credentials.json ◄────┐      │                    │
│                             │      │                    │
└─────────────────────────────┼──────┼─────────────────────┘
                              │      │
                              │      │
┌─────────────────────────────┼──────┼─────────────────────┐
│         Backend Container   │      │                     │
│                             │      │                     │
│  /app/                      │      │                     │
│  ├── credentials.json ◄─────┘      │                     │
│  ├── data/ ◄───────────────────────┘                     │
│  ├── logs/ ◄───────────────────────────────┐             │
│  └── uploads/ ◄────────────────────────────┤             │
│                                             │             │
│  All data persists on host!                 │             │
└─────────────────────────────────────────────┼─────────────┘
                                              │
                                    Persists across restarts
```

## Build Process

### Frontend Build

```
┌──────────────────┐
│  Source Code     │
│  (React + TS)    │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│  Stage 1:        │
│  Builder         │
│  - node:20       │
│  - bun install   │
│  - bun build     │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│  Built Assets    │
│  /app/dist/      │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│  Stage 2:        │
│  Production      │
│  - nginx:alpine  │
│  - Copy dist/    │
│  - nginx.conf    │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│  Final Image     │
│  ~100MB          │
└──────────────────┘
```

### Backend Build

```
┌──────────────────┐
│  Source Code     │
│  (Python)        │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│  Base Image      │
│  python:3.11-slim│
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│  Install Poetry  │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│  Install Deps    │
│  poetry install  │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│  Copy Code       │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│  Final Image     │
│  ~500MB          │
└──────────────────┘
```

## Deployment Workflow

```
┌─────────────────┐
│  1. Prepare     │
│  - Clone repo   │
│  - Set .env     │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  2. Build       │
│  - Backend img  │
│  - Frontend img │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  3. Start       │
│  - Backend      │
│  - Frontend     │
│  - Network      │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  4. Initialize  │
│  - Setup DB     │
│  - Mock data    │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  5. Verify      │
│  - Health check │
│  - Test UI      │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  6. Running ✓   │
└─────────────────┘
```

## Network Ports

```
External Access          Internal Docker Network
───────────────          ─────────────────────────

Port 80                  Frontend Container
(HTTP)      ────────────▶ :80  (nginx)
                              │
                              │ Proxy /api/*
                              ▼
Port 8000                Backend Container
(API)       ────────────▶ :8000 (uvicorn)


Port 443                 Frontend Container
(HTTPS)     ────────────▶ :443  (nginx with SSL)
(Production)
```

## SSL/HTTPS Architecture (Production)

```
                Internet
                   │
                   │ HTTPS (443)
                   ▼
        ┌──────────────────┐
        │   Let's Encrypt  │
        │   Certificate    │
        └────────┬─────────┘
                 │
                 ▼
        ┌──────────────────┐
        │   Nginx (SSL)    │
        │   - Cert verify  │
        │   - TLS 1.2/1.3  │
        │   - HTTP → HTTPS │
        └────────┬─────────┘
                 │
    ┌────────────┴────────────┐
    │                         │
    ▼                         ▼
Static Files            Backend API
(React App)            (FastAPI)
```

## File System Layout

```
gradent/
├── Dockerfile.backend          # Backend container definition
├── Dockerfile.frontend         # Frontend container definition
├── docker-compose.yml          # Dev/staging orchestration
├── docker-compose.prod.yml     # Production overrides
├── .dockerignore               # Build exclusions
├── .env                        # Environment config (YOU CREATE)
├── .env.example                # Template
├── Makefile                    # Command shortcuts
│
├── deployment/                 # Deployment configs
│   ├── DEPLOYMENT_GUIDE.md     # Full guide
│   ├── QUICKSTART.md           # Quick start
│   ├── README.md               # Overview
│   ├── SUMMARY.md              # What was created
│   ├── ARCHITECTURE.md         # This file
│   ├── deploy.sh               # Automated script
│   ├── nginx.conf              # HTTP config
│   └── nginx-ssl.conf          # HTTPS config
│
├── data/                       # Persistent data (created on run)
│   ├── study_assistant.db      # SQLite
│   └── vector_db/              # Chroma
│
├── logs/                       # Application logs
│   └── *.log
│
└── uploads/                    # User uploads
    └── *
```

## Resource Requirements

### Minimum Requirements
- **CPU**: 1 core
- **RAM**: 2 GB
- **Disk**: 10 GB
- **OS**: Ubuntu 20.04+

### Recommended for Production
- **CPU**: 2+ cores
- **RAM**: 4+ GB
- **Disk**: 20+ GB SSD
- **OS**: Ubuntu 22.04 LTS

### Container Resource Usage
```
Backend:  ~300-500 MB RAM, 10-30% CPU
Frontend: ~50-100 MB RAM,   1-5% CPU
Total:    ~400-600 MB RAM
```

## Scaling Options

### Horizontal Scaling (Multiple Backend Instances)

```
              ┌─────────────┐
              │   Nginx     │
              │ Load Balance│
              └──────┬──────┘
                     │
        ┌────────────┼────────────┐
        │            │            │
   ┌────▼───┐   ┌───▼────┐  ┌────▼───┐
   │Backend1│   │Backend2│  │Backend3│
   └────────┘   └────────┘  └────────┘
        │            │            │
        └────────────┴────────────┘
                     │
              ┌──────▼──────┐
              │  Shared DB  │
              └─────────────┘
```

### Vertical Scaling (Resource Limits)

```yaml
services:
  backend:
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 2G
        reservations:
          cpus: '1'
          memory: 1G
```

## Security Layers

```
┌─────────────────────────────────────┐
│  1. Firewall (UFW)                  │
│     - Allow 80, 443, 22 only        │
└──────────────┬──────────────────────┘
               │
┌──────────────▼──────────────────────┐
│  2. Nginx Security Headers          │
│     - X-Frame-Options               │
│     - X-Content-Type-Options        │
│     - XSS Protection                │
└──────────────┬──────────────────────┘
               │
┌──────────────▼──────────────────────┐
│  3. Docker Network Isolation        │
│     - Internal network only         │
│     - No direct container access    │
└──────────────┬──────────────────────┘
               │
┌──────────────▼──────────────────────┐
│  4. Environment Variables           │
│     - API keys not in images        │
│     - .env file on host only        │
└──────────────┬──────────────────────┘
               │
┌──────────────▼──────────────────────┐
│  5. SSL/TLS Encryption              │
│     - HTTPS only in production      │
│     - TLS 1.2+ required             │
└─────────────────────────────────────┘
```

This architecture provides:
- ✅ Container isolation
- ✅ Data persistence
- ✅ Easy scaling
- ✅ Security layers
- ✅ Simple maintenance
- ✅ Fast deployment
