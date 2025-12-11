# Docker Setup Guide

## Overview

This project uses Docker and Docker Compose to run the application with a PostgreSQL database container. This makes setup and deployment much easier!

## Prerequisites

1. **Docker Desktop** (Windows/Mac) or **Docker Engine** (Linux)
   - Download from: https://www.docker.com/products/docker-desktop
   - Verify installation: `docker --version` and `docker-compose --version`

2. **API Keys** (you'll need these):
   - Pinecone API Key ([Get one here](https://www.pinecone.io/))
   - Google Gemini API Key ([Get one here](https://makersuite.google.com/app/apikey))

## First Time Setup

### Step 1: Clone/Download the Project

Navigate to your project directory:
```bash
cd "C:\Users\User\projects\medical ChatBot"
```

### Step 2: Create Environment File

Create a `.env` file in the project root:

```ini
PINECONE_API_KEY=your_pinecone_api_key_here
GOOGLE_API_KEY=your_gemini_api_key_here
SECRET_KEY=your-random-secret-key-here
GEMINI_MODEL=gemini-2.5-flash
```

**Important**: Replace the placeholder values with your actual API keys!

### Step 3: Build and Start Containers

```bash
docker-compose up --build
```

This will:
- Build the application Docker image
- Pull PostgreSQL image
- Start both containers
- Create the database
- Initialize database tables
- Start the Flask application

### Step 4: Access the Application

Open your browser and go to:
```
http://localhost:8080
```

Wait for: "Running on http://0.0.0.0:8080" in the logs

## Running the Project

### Quick Start (Everything Running)
```bash
docker-compose up
```

### Start in Background (Detached Mode)
```bash
docker-compose up -d
```

### Stop Containers
```bash
docker-compose down
```

### Stop and Remove Volumes (⚠️ Deletes Database Data)
```bash
docker-compose down -v
```

### View Logs
```bash
# All services
docker-compose logs

# Specific service
docker-compose logs app
docker-compose logs db

# Follow logs (like tail -f)
docker-compose logs -f app
```

## Common Commands

### Check Container Status
```bash
docker-compose ps
```

### Restart Services
```bash
docker-compose restart
```

### Restart Specific Service
```bash
docker-compose restart app
docker-compose restart db
```

### Rebuild After Code Changes
```bash
docker-compose up --build
```

### Access Database Directly
```bash
# Connect to PostgreSQL container
docker-compose exec db psql -U medicalbot -d medical_chatbot

# Or from outside Docker
psql -h localhost -p 5432 -U medicalbot -d medical_chatbot
```

### Access Application Container Shell
```bash
docker-compose exec app bash
```

### Run Database Migrations (if needed)
```bash
docker-compose exec app python -c "from app import app, db; app.app_context().push(); db.create_all()"
```

## Docker Services

### 1. Database (PostgreSQL)
- **Container**: `medical_chatbot_db`
- **Port**: `5432`
- **Database**: `medical_chatbot`
- **User**: `medicalbot`
- **Password**: `medicalbot_password`
- **Volume**: `postgres_data` (persists data)

### 2. Application (Flask)
- **Container**: `medical_chatbot_app`
- **Port**: `8080`
- **Depends on**: Database service
- **Volumes**: 
  - `./data/uploads` → `/app/data/uploads` (PDF uploads)
  - `./app.py`, `./src`, `./templates`, `./static` (code hot-reload)

## Environment Variables

The application uses these environment variables (set in `.env`):

- `DATABASE_URL`: Automatically set by docker-compose
- `PINECONE_API_KEY`: Your Pinecone API key
- `GOOGLE_API_KEY`: Your Gemini API key
- `SECRET_KEY`: Flask secret key (change in production!)
- `GEMINI_MODEL`: Gemini model name (default: `gemini-2.5-flash`)

## Troubleshooting

### Port Already in Use
If port 8080 or 5432 is already in use:
```bash
# Stop other services using those ports, or
# Edit docker-compose.yml to use different ports
```

### Database Connection Errors
```bash
# Check if database container is healthy
docker-compose ps

# Check database logs
docker-compose logs db

# Restart database
docker-compose restart db
```

### Application Won't Start
```bash
# Check application logs
docker-compose logs app

# Rebuild containers
docker-compose up --build

# Check environment variables
docker-compose exec app env | grep -E "DATABASE|PINECONE|GOOGLE|SECRET|GEMINI"
```

### Reset Everything (⚠️ Deletes All Data)
```bash
# Stop and remove everything (⚠️ Deletes all data)
docker-compose down -v

# Remove images
docker-compose down --rmi all

# Start fresh
docker-compose up --build
```

### Database Data Persistence
Database data is stored in a Docker volume (`postgres_data`). To backup:

```bash
# Backup database
docker-compose exec db pg_dump -U medicalbot medical_chatbot > backup.sql

# Restore database
docker-compose exec -T db psql -U medicalbot medical_chatbot < backup.sql
```

## Development Workflow

### Making Code Changes
1. Edit code files
2. Restart the app container:
   ```bash
   docker-compose restart app
   ```
   Or rebuild:
   ```bash
   docker-compose up --build app
   ```

### Adding New Dependencies
1. Add to `requirements.txt`
2. Rebuild:
   ```bash
   docker-compose up --build
   ```

## Production Deployment

For production, you'll want to:

1. **Change `SECRET_KEY`** to a strong random value
2. **Use environment-specific database credentials**
3. **Set up proper backups**
4. **Use a reverse proxy (nginx)**
5. **Enable HTTPS**
6. **Set resource limits** in docker-compose.yml
7. **Use environment variables** for all sensitive data
8. **Disable debug mode** in Flask

## Quick Reference

```bash
# Start everything
docker-compose up

# Start in background
docker-compose up -d

# Stop everything
docker-compose down

# View logs
docker-compose logs -f

# Rebuild after changes
docker-compose up --build

# Access database
docker-compose exec db psql -U medicalbot -d medical_chatbot

# Run tests
docker-compose exec app pytest
```

## Next Steps After Setup

1. **Register an Account**: Go to http://localhost:8080 and register
2. **Upload Documents**: Upload your medical PDF files
3. **Start Chatting**: Ask medical questions!
4. **Check Logs**: Monitor with `docker-compose logs -f`

