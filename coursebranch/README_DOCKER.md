# Docker Deployment Guide for Proxmox

## Prerequisites
- Docker installed on your Proxmox LXC container or VM
- Docker Compose installed

## Quick Start

### 1. Clone the repository
```bash
git clone <your-repo-url>
cd coursebranch
```

### 2. Configure environment variables
```bash
cp .env.example .env
nano .env  # Edit with your secure values
```

**Important**: Change these values in `.env`:
- `SECRET_KEY` - Generate new one: `python -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())'`
- `POSTGRES_PASSWORD` - Use a strong password
- `ALLOWED_HOSTS` - Add your domain/IP

### 3. Build and run
```bash
docker-compose up -d --build
```

### 4. Create superuser (first time only)
```bash
docker-compose exec web python manage.py createsuperuser
```

## Management Commands

### View logs
```bash
docker-compose logs -f
```

### Restart services
```bash
docker-compose restart
```

### Stop services
```bash
docker-compose down
```

### Update application
```bash
git pull
docker-compose down
docker-compose up -d --build
```

### Database backup
```bash
docker-compose exec db pg_dump -U coursebranch_user coursebranch > backup.sql
```

### Database restore
```bash
cat backup.sql | docker-compose exec -T db psql -U coursebranch_user coursebranch
```

## Port Mapping
- **80** - Nginx (web interface)
- **8000** - Django (internal, proxied by Nginx)
- **5432** - PostgreSQL (internal, not exposed)

## File Structure
```
coursebranch/
├── Dockerfile              # Django container definition
├── docker-compose.yml      # Multi-container orchestration
├── nginx.conf             # Nginx configuration
├── requirements.txt       # Python dependencies
├── .env                   # Environment variables (create from .env.example)
└── .dockerignore          # Files to exclude from Docker build
```

## Troubleshooting

### Check container status
```bash
docker-compose ps
```

### Access Django shell
```bash
docker-compose exec web python manage.py shell
```

### Database connection issues
```bash
docker-compose exec db psql -U coursebranch_user -d coursebranch
```

### Clear all data and restart fresh
```bash
docker-compose down -v
docker-compose up -d --build
docker-compose exec web python manage.py migrate
docker-compose exec web python manage.py createsuperuser
```

## Production Recommendations

1. **Use a reverse proxy** (Traefik/Caddy) for SSL/TLS
2. **Set up automated backups** for PostgreSQL
3. **Monitor logs** with proper logging solution
4. **Resource limits** in docker-compose.yml if needed
5. **Health checks** already configured for database

