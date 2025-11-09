# Gradent Deployment Guide

This guide walks you through deploying the Gradent Study Assistant (frontend + backend) to an Ubuntu VM using Docker.

## 🚀 Quick Deploy (Automated Script)

**Want to skip the manual steps?** Use our fully automated deployment script:

```bash
wget https://raw.githubusercontent.com/flatala/gradent/main/deploy-vm.sh && chmod +x deploy-vm.sh && ./deploy-vm.sh
```

This single command will:
- Install all prerequisites (Docker, dependencies)
- Configure firewall
- Clone and configure the application
- Build and deploy everything automatically
- Only prompt for your OpenAI API key

**See [DEPLOY_VM_README.md](../DEPLOY_VM_README.md) for details.**

---

## Manual Deployment Guide

If you prefer to understand each step or need manual control, follow this guide:

## Prerequisites

- Ubuntu 20.04+ VM with SSH access
- At least 2GB RAM and 10GB disk space
- Domain name (optional, for production)
- OpenAI API key

## Table of Contents

1. [Initial Server Setup](#1-initial-server-setup)
2. [Install Docker and Docker Compose](#2-install-docker-and-docker-compose)
3. [Deploy the Application](#3-deploy-the-application)
4. [Configuration](#4-configuration)
5. [Running the Application](#5-running-the-application)
6. [Monitoring and Maintenance](#6-monitoring-and-maintenance)
7. [SSL/HTTPS Setup (Production)](#7-sslhttps-setup-production)
8. [Troubleshooting](#8-troubleshooting)

---

## 1. Initial Server Setup

### Connect to your Ubuntu VM

```bash
ssh your-username@your-vm-ip
```

### Update system packages

```bash
sudo apt update && sudo apt upgrade -y
```

### Install basic utilities

```bash
sudo apt install -y git curl wget vim ufw
```

### Configure firewall (optional but recommended)

```bash
# Allow SSH
sudo ufw allow 22/tcp

# Allow HTTP/HTTPS
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp

# Enable firewall
sudo ufw --force enable
```

---

## 2. Install Docker and Docker Compose

### Install Docker

```bash
# Remove old versions
sudo apt remove docker docker-engine docker.io containerd runc

# Install dependencies
sudo apt install -y apt-transport-https ca-certificates curl software-properties-common

# Add Docker's official GPG key
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg

# Add Docker repository
echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# Install Docker
sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

# Verify installation
sudo docker --version
```

### Add your user to the docker group (optional, avoids using sudo)

```bash
sudo usermod -aG docker $USER
newgrp docker

# Test without sudo
docker ps
```

### Verify Docker Compose

```bash
docker compose version
```

---

## 3. Deploy the Application

### Clone the repository

```bash
cd ~
git clone https://github.com/flatala/gradent.git
cd gradent
```

Or if you're uploading from your local machine:

```bash
# From your local machine
scp -r c:\Users\rowde\Documents\GitHub\gradent your-username@your-vm-ip:~/
```

---

## 4. Configuration

### Create environment file

```bash
cd ~/gradent
cp .env.example .env
nano .env  # or use vim/vi
```

**Required configuration:**

```bash
OPENAI_API_KEY=sk-your-actual-api-key-here
```

**Optional configuration:**

```bash
# Custom OpenAI endpoint
OPENAI_BASE_URL=https://your-gateway/v1

# Discord notifications
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/...

# Google Calendar
GOOGLE_CLIENT_ID=your-id
GOOGLE_CLIENT_SECRET=your-secret
```

### Set up Google Calendar credentials (if using)

If you're using Google Calendar integration:

```bash
# Copy your credentials.json file to the project root
scp credentials.json your-username@your-vm-ip:~/gradent/
```

### Create necessary directories

```bash
mkdir -p data logs uploads data/vector_db
```

---

## 5. Running the Application

### Build and start the containers

```bash
# Build images and start services
docker compose up -d --build
```

This will:
- Build the backend Docker image with Python and all dependencies
- Build the frontend Docker image with Node/Bun and Nginx
- Start both services with proper networking
- Expose port 80 (frontend) and 8000 (backend)

### Check container status

```bash
docker compose ps
```

You should see:
```
NAME                IMAGE               STATUS         PORTS
gradent-backend     gradent-backend     Up (healthy)   0.0.0.0:8000->8000/tcp
gradent-frontend    gradent-frontend    Up (healthy)   0.0.0.0:80->80/tcp
```

### View logs

```bash
# All services
docker compose logs -f

# Specific service
docker compose logs -f backend
docker compose logs -f frontend
```

### Initialize the database (first time only)

```bash
# Run setup scripts inside the container
docker compose exec backend python scripts/setup_all.py
```

This will create mock data for testing. You can skip this if you plan to use real data.

---

## 6. Monitoring and Maintenance

### Check application health

```bash
# Backend health
curl http://localhost:8000/health

# Frontend
curl http://localhost/
```

### View resource usage

```bash
docker stats
```

### Restart services

```bash
# Restart all services
docker compose restart

# Restart specific service
docker compose restart backend
docker compose restart frontend
```

### Stop services

```bash
docker compose down
```

### Update the application

```bash
# Pull latest code
cd ~/gradent
git pull

# Rebuild and restart
docker compose up -d --build
```

### Backup data

```bash
# Backup database and vector DB
tar -czf gradent-backup-$(date +%Y%m%d).tar.gz data/ logs/

# Download to local machine
scp your-username@your-vm-ip:~/gradent-backup-*.tar.gz ./
```

### Clean up Docker resources

```bash
# Remove unused containers, images, networks
docker system prune -a

# Remove old volumes (careful!)
docker volume prune
```

---

## 7. SSL/HTTPS Setup (Production)

For production deployment with a domain name, use Let's Encrypt for free SSL certificates.

### Install Certbot

```bash
sudo apt install -y certbot python3-certbot-nginx
```

### Update docker-compose.yml for SSL

Create `docker-compose.prod.yml`:

```yaml
version: '3.8'

services:
  backend:
    extends:
      file: docker-compose.yml
      service: backend

  frontend:
    extends:
      file: docker-compose.yml
      service: frontend
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./deployment/nginx-ssl.conf:/etc/nginx/conf.d/default.conf
      - /etc/letsencrypt:/etc/letsencrypt:ro
```

### Get SSL certificate

```bash
# Stop containers temporarily
docker compose down

# Get certificate (replace with your domain)
sudo certbot certonly --standalone -d yourdomain.com -d www.yourdomain.com

# Restart with SSL config
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

### Auto-renewal

Certbot automatically sets up renewal. Test it:

```bash
sudo certbot renew --dry-run
```

---

## 8. Troubleshooting

### Container won't start

```bash
# Check logs for errors
docker compose logs backend
docker compose logs frontend

# Check if ports are already in use
sudo netstat -tulpn | grep :80
sudo netstat -tulpn | grep :8000
```

### Backend errors

```bash
# Access backend container shell
docker compose exec backend bash

# Check Python environment
python --version
poetry show

# Test API manually
curl http://localhost:8000/health
```

### Frontend not loading

```bash
# Check nginx logs
docker compose logs frontend

# Verify nginx config
docker compose exec frontend nginx -t

# Check if backend is accessible from frontend
docker compose exec frontend wget -O- http://backend:8000/health
```

### Database issues

```bash
# Reset database
docker compose exec backend python scripts/rebuild_database.py

# Check database file
docker compose exec backend ls -lh data/
```

### Port conflicts

If ports 80 or 8000 are already in use, modify `docker-compose.yml`:

```yaml
services:
  backend:
    ports:
      - "8001:8000"  # Changed from 8000:8000
  
  frontend:
    ports:
      - "8080:80"    # Changed from 80:80
```

### Out of memory

```bash
# Check memory usage
free -h
docker stats

# Reduce container memory if needed (add to docker-compose.yml)
services:
  backend:
    mem_limit: 512m
  frontend:
    mem_limit: 256m
```

### API key issues

```bash
# Verify environment variables are loaded
docker compose exec backend env | grep OPENAI
```

---

## Quick Reference Commands

```bash
# Start application
docker compose up -d

# Stop application
docker compose down

# View logs
docker compose logs -f

# Restart services
docker compose restart

# Update application
git pull && docker compose up -d --build

# Check status
docker compose ps

# Backup data
tar -czf backup.tar.gz data/ logs/

# Access backend shell
docker compose exec backend bash

# Run database migrations
docker compose exec backend python scripts/migrate_database.py
```

---

## Accessing the Application

- **Frontend**: http://your-vm-ip/ or http://yourdomain.com
- **Backend API**: http://your-vm-ip:8000 or http://yourdomain.com/api
- **API Documentation**: http://your-vm-ip:8000/docs

---

## Support

For issues or questions:
- Check the logs: `docker compose logs -f`
- Review error messages in the container output
- Ensure all environment variables are set correctly
- Verify network connectivity between containers

---

## Security Considerations

1. **Always use HTTPS in production** (see SSL setup above)
2. **Keep your `.env` file secure** - never commit it to git
3. **Regularly update dependencies** and Docker images
4. **Use strong passwords** for any database or admin interfaces
5. **Configure firewall rules** to only expose necessary ports
6. **Monitor logs** for suspicious activity
7. **Regular backups** of data and configuration

---

## Performance Optimization

### For better performance:

1. **Use Docker volumes for persistent data** (already configured)
2. **Enable nginx caching** for static assets (already configured)
3. **Monitor resource usage** with `docker stats`
4. **Scale services** if needed:

```yaml
# docker-compose.yml
services:
  backend:
    deploy:
      replicas: 3  # Run 3 backend instances
```

5. **Use a reverse proxy** like Traefik or Caddy for advanced routing

---

## Next Steps

After successful deployment:

1. ✅ Test all API endpoints: http://your-vm-ip:8000/docs
2. ✅ Verify frontend loads: http://your-vm-ip
3. ✅ Set up monitoring (optional): Prometheus + Grafana
4. ✅ Configure automated backups
5. ✅ Set up SSL certificates for production
6. ✅ Configure domain DNS records
7. ✅ Set up CI/CD pipeline (optional)

---

**Congratulations! Your Gradent Study Assistant is now deployed! 🎉**
