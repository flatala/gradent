# Deployment Files

This directory contains all the files needed to deploy the Gradent Study Assistant using Docker.

## Files Overview

| File | Description |
|------|-------------|
| `DEPLOYMENT_GUIDE.md` | Complete deployment guide with detailed instructions |
| `QUICKSTART.md` | Quick reference for fast deployment |
| `deploy.sh` | Automated deployment script for Ubuntu |
| `nginx.conf` | Nginx configuration for frontend (HTTP) |
| `nginx-ssl.conf` | Nginx configuration with SSL/HTTPS support |

## Quick Start

1. **Read the Quick Start guide:**
   ```bash
   cat deployment/QUICKSTART.md
   ```

2. **Or run the automated deployment:**
   ```bash
   chmod +x deployment/deploy.sh
   ./deployment/deploy.sh
   ```

## Files in Root Directory

These deployment files are also in the project root:

- `Dockerfile.backend` - Backend Docker image definition
- `Dockerfile.frontend` - Frontend Docker image definition
- `docker-compose.yml` - Development/staging configuration
- `docker-compose.prod.yml` - Production configuration with SSL
- `.dockerignore` - Files to exclude from Docker builds
- `.env.example` - Environment variable template
- `Makefile` - Convenient shortcuts for Docker commands

## Using the Deployment Script

The `deploy.sh` script automates the entire deployment process:

```bash
./deployment/deploy.sh
```

It will:
1. Check for Docker and Docker Compose
2. Verify environment configuration
3. Create necessary directories
4. Build and start containers
5. Wait for services to be healthy
6. Optionally initialize the database

## Manual Deployment

If you prefer manual control:

```bash
# 1. Configure environment
cp .env.example .env
nano .env

# 2. Build and start
docker compose up -d --build

# 3. Initialize database (optional)
docker compose exec backend python scripts/setup_all.py

# 4. Check status
docker compose ps
```

## Using Makefile

For convenience, use the Makefile commands:

```bash
make build      # Build images
make up         # Start services
make logs       # View logs
make status     # Check status
make down       # Stop services
make backup     # Backup data
```

See all commands: `make help`

## Production Deployment

For production with SSL/HTTPS:

1. **Get SSL certificate** (using Let's Encrypt):
   ```bash
   sudo certbot certonly --standalone -d yourdomain.com
   ```

2. **Update nginx-ssl.conf** with your domain

3. **Start with production config**:
   ```bash
   docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d
   ```

Or use Makefile:
```bash
make prod-up
```

## Configuration Files

### nginx.conf
Default configuration for HTTP-only deployment. Used in development and staging.

### nginx-ssl.conf
Production configuration with SSL/HTTPS support. Includes:
- SSL certificate configuration
- HTTP to HTTPS redirect
- Security headers
- Optimized caching

Update the domain in this file before production deployment.

## Environment Variables

Required:
- `OPENAI_API_KEY` - Your OpenAI API key

Optional:
- `OPENAI_BASE_URL` - Custom OpenAI endpoint
- `DISCORD_WEBHOOK_URL` - Discord notifications
- `GOOGLE_CLIENT_ID` - Google Calendar integration
- `GOOGLE_CLIENT_SECRET` - Google Calendar integration

See `.env.example` for all available options.

## Troubleshooting

**Containers won't start:**
```bash
docker compose logs
```

**Port conflicts:**
Edit `docker-compose.yml` ports section.

**Permission issues:**
```bash
sudo chown -R $USER:$USER data/ logs/ uploads/
```

**Reset everything:**
```bash
docker compose down -v
docker system prune -a
```

## Directory Structure After Deployment

```
gradent/
├── data/                    # Persistent data (mounted in backend)
│   ├── study_assistant.db   # SQLite database
│   └── vector_db/           # Chroma vector store
├── logs/                    # Application logs
├── uploads/                 # User uploads
└── deployment/              # This directory
```

## Health Checks

Both containers have health checks configured:

- Backend: `curl http://localhost:8000/health`
- Frontend: `curl http://localhost/`

View health status:
```bash
docker compose ps
```

## Updating the Application

```bash
# Pull latest code
git pull

# Rebuild and restart
docker compose up -d --build
```

Or use Makefile:
```bash
make update
```

## Backup and Restore

### Backup
```bash
make backup
# Or manually:
tar -czf backup.tar.gz data/ logs/
```

### Restore
```bash
tar -xzf backup.tar.gz
docker compose restart
```

## Support

- Full documentation: `DEPLOYMENT_GUIDE.md`
- Quick reference: `QUICKSTART.md`
- Project README: `../README.md`
- API documentation: http://localhost:8000/docs

## Security Notes

1. Never commit `.env` file to version control
2. Use strong API keys and tokens
3. Enable firewall on production servers
4. Use HTTPS in production (see SSL setup)
5. Regularly update Docker images and dependencies
6. Monitor logs for suspicious activity

## Performance Tips

1. Monitor resource usage: `docker stats`
2. Check logs regularly: `docker compose logs -f`
3. Use volume mounts for persistent data (already configured)
4. Enable nginx caching (already configured)
5. Consider scaling backend if needed

## Next Steps After Deployment

1. ✅ Access frontend: http://your-ip/
2. ✅ Check API docs: http://your-ip:8000/docs
3. ✅ Test all features
4. ✅ Set up monitoring
5. ✅ Configure backups
6. ✅ Set up SSL for production
7. ✅ Configure domain DNS

---

For detailed instructions, always refer to **DEPLOYMENT_GUIDE.md**.
