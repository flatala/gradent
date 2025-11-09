# Quick Start - Docker Deployment

This is a quick reference for deploying Gradent with Docker. For detailed instructions, see [DEPLOYMENT_GUIDE.md](./DEPLOYMENT_GUIDE.md).

## Prerequisites

- Docker and Docker Compose installed
- OpenAI API key
- Ubuntu VM or Linux system

## Quick Deploy (3 steps)

### 1. Clone and configure

```bash
git clone https://github.com/flatala/gradent.git
cd gradent
cp .env.example .env
nano .env  # Add your OPENAI_API_KEY
```

### 2. Deploy with one command

```bash
chmod +x deployment/deploy.sh
./deployment/deploy.sh
```

### 3. Access your application

- Frontend: http://your-vm-ip/
- Backend API: http://your-vm-ip:8000
- API Docs: http://your-vm-ip:8000/docs

## Manual Deployment

```bash
# Build and start
docker compose up -d --build

# Initialize database (optional)
docker compose exec backend python scripts/setup_all.py

# Check status
docker compose ps

# View logs
docker compose logs -f
```

## Common Commands

```bash
# Stop
docker compose down

# Restart
docker compose restart

# Update
git pull && docker compose up -d --build

# Logs
docker compose logs -f backend
docker compose logs -f frontend

# Shell access
docker compose exec backend bash
```

## Troubleshooting

**Containers won't start:**
```bash
docker compose logs
```

**Port conflicts:**
Edit `docker-compose.yml` to change ports 80 or 8000 to different values.

**API key issues:**
```bash
docker compose exec backend env | grep OPENAI
```

## Architecture

```
┌─────────────┐      ┌─────────────┐
│  Frontend   │─────▶│   Backend   │
│   (Nginx)   │      │  (FastAPI)  │
│   Port 80   │      │  Port 8000  │
└─────────────┘      └─────────────┘
                            │
                     ┌──────┴──────┐
                     │   SQLite    │
                     │  Vector DB  │
                     └─────────────┘
```

## Production Notes

- Use SSL/HTTPS (see full guide)
- Configure firewall (ports 80, 443, 22)
- Set up automated backups
- Monitor logs and resources
- Keep Docker images updated

For complete documentation, see [DEPLOYMENT_GUIDE.md](./DEPLOYMENT_GUIDE.md).
