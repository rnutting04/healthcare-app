# Healthcare Microservices System

A comprehensive microservice architecture for a healthcare system with role-based access control for Patients and Administrators.

## Architecture Overview

The system consists of 7 main services:

1. **Auth Service** (Port 8001): Handles authentication, authorization, and JWT token management
2. **Patient Service** (Port 8002): Manages patient data and profile information
3. **Clinician Service** (Port 8003): Manages clinician authentication and dashboard
4. **Database Service** (Port 8004): Centralized database operations with Redis caching
5. **Admin Service** (Port 8005): Administrative dashboard and user management
6. **File Service** (Port 8006): Secure file storage and management
7. **Nginx**: Reverse proxy for routing requests to appropriate services

## Technology Stack

- **Backend**: Python/Django with Django REST Framework
- **Database**: PostgreSQL with connection pooling
- **Cache**: Redis for session management and caching
- **Frontend**: HTML5 with Tailwind CSS
- **Authentication**: JWT tokens with role-based access control
- **Deployment**: Docker containers on Render.com

## Getting Started

### Prerequisites

- Docker and Docker Compose
- Python 3.11+
- Node.js (for Tailwind CSS build)

### Local Development

1. Clone the repository:
```bash
git clone <repository-url>
cd healthcare-app
```

2. Copy environment variables:
```bash
cp .env.example .env
# Edit .env with your configuration
```

3. Start all services:
```bash
docker-compose up -d
```

4. Run migrations:
```bash
docker-compose exec database-service python manage.py migrate
docker-compose exec auth-service python manage.py migrate
docker-compose exec patient-service python manage.py migrate
docker-compose exec clinician-service python manage.py migrate
```

5. Create a superuser:
```bash
docker-compose exec auth-service python manage.py createsuperuser
```

6. Access the application:
- Main app: http://localhost
- Auth Service: http://localhost:8001
- Patient Service: http://localhost:8002
- Clinician Service: http://localhost:8003
- Database Service: http://localhost:8004
- Admin Service: http://localhost:8005

## API Documentation

Each service provides Swagger documentation:
- Auth Service: http://localhost:8001/swagger/
- Patient Service: http://localhost:8002/swagger/
- Clinician Service: http://localhost:8003/swagger/
- Database Service: http://localhost:8004/swagger/
- Admin Service: http://localhost:8005/swagger/

## User Roles

1. **Patient**: Can view and manage their profile information
2. **Clinician**: Can access clinician dashboard and manage patient care (stub implementation)
3. **Admin**: Full access to all system features

## Deployment

### Render.com Deployment

1. Push code to GitHub
2. Connect your GitHub repository to Render.com
3. Deploy using the `render.yaml` configuration
4. Set required environment variables in Render dashboard

### Environment Variables

See `.env.example` for all required environment variables. Key variables include:
- `SECRET_KEY`: Django secret key
- `JWT_SECRET_KEY`: JWT signing key
- `DATABASE_URL`: PostgreSQL connection string
- `REDIS_URL`: Redis connection string

## Security Features

- JWT token-based authentication
- Role-based access control (RBAC)
- HTTPS enforcement in production
- CORS properly configured
- Input validation and sanitization
- Rate limiting on authentication endpoints
- Environment-based configuration

## Health Checks

Each service exposes a health endpoint:
- Auth: `/health/auth`
- Patient: `/health/patient`
- Clinician: `/health/clinician`
- Database: `/health/database`
- Admin: `/health/admin`
- Combined: `/health`

## Development Workflow

1. Make changes to service code
2. Rebuild affected services: `docker-compose build <service-name>`
3. Restart services: `docker-compose restart <service-name>`
4. Run tests: `docker-compose exec <service-name> python manage.py test`

## License

This project is licensed under the MIT License.