# FastAPI Backend

A professional FastAPI backend application with authentication, user management, and modern development practices.

## Features

- 🔐 **JWT Authentication** - Secure token-based authentication
- 👥 **User Management** - Complete CRUD operations for users
- 🗄️ **SQLAlchemy ORM** - Database abstraction with SQLite support
- 📝 **Pydantic Validation** - Request/response data validation
- 🔒 **Role-based Access Control** - Superuser and regular user roles
- 🌐 **CORS Support** - Cross-origin resource sharing
- 📚 **Auto-generated API Docs** - Interactive Swagger UI and ReDoc
- 🧪 **Testing Ready** - Pytest configuration included
- 🎨 **Code Quality** - Black, isort, and mypy configuration

## Quick Start

### Prerequisites

- Python 3.8 or higher
- pip or uv package manager

### Installation

1. **Clone the repository**
   ```bash
   git clone <your-repo-url>
   cd backend
   ```

2. **Install dependencies**
   ```bash
   # Using pip
   pip install -e .
   
   # Or using uv
   uv sync
   ```

3. **Run the application**
   ```bash
   # Using uvicorn directly
   uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
   
   # Or using the script
   python -m backend.main
   ```

4. **Access the API**
   - API Documentation: http://localhost:8000/api/v1/docs
   - ReDoc Documentation: http://localhost:8000/api/v1/redoc
   - Health Check: http://localhost:8000/health

## Default Superuser

The application automatically creates a default superuser on first run:

- **Email**: admin@example.com
- **Password**: admin123

⚠️ **Important**: Change these credentials in production!

## API Endpoints

### Authentication
- `POST /api/v1/auth/login` - Login and get access token

### Users
- `GET /api/v1/users` - List all users (superuser only)
- `POST /api/v1/users` - Create new user (superuser only)
- `GET /api/v1/users/me` - Get current user profile
- `PUT /api/v1/users/me` - Update current user profile
- `GET /api/v1/users/{user_id}` - Get specific user by ID

### Health
- `GET /health` - Health check endpoint
- `GET /` - Root endpoint with API information

## Project Structure

```
src/backend/
├── api/
│   └── endpoint/
│       └── routes.py          # Main API routes
├── core/
│   ├── config.py              # Application configuration
│   └── database.py            # Database setup
├── dependencies/
│   └── auth.py                # Authentication dependencies
├── middleware/
│   └── cors.py                # CORS middleware
├── models/
│   └── user.py                # SQLAlchemy models
├── schemas/
│   ├── user.py                # Pydantic schemas
│   └── token.py               # Token schemas
├── utils/
│   └── security.py            # Security utilities
└── main.py                    # FastAPI application
```

## Environment Variables

Create a `.env` file in the root directory:

```env
# API Configuration
API_V1_STR=/api/v1
PROJECT_NAME=FastAPI Backend
VERSION=1.0.0

# Security
SECRET_KEY=your-secret-key-here-change-in-production
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# Database
DATABASE_URL=sqlite:///./app.db

# CORS
BACKEND_CORS_ORIGINS=["http://localhost:3000","http://localhost:8080"]

# Environment
ENVIRONMENT=development
DEBUG=true
```

## Development

### Code Quality

```bash
# Format code
black src/
isort src/

# Type checking
mypy src/

# Linting
flake8 src/
```

### Testing

```bash
# Run tests
pytest

# Run tests with coverage
pytest --cov=backend
```

### Database Migrations

```bash
# Initialize Alembic (first time)
alembic init alembic

# Create migration
alembic revision --autogenerate -m "Description"

# Apply migrations
alembic upgrade head
```

## Production Deployment

1. **Set environment variables**
   - Change `SECRET_KEY` to a secure random string
   - Set `ENVIRONMENT=production`
   - Set `DEBUG=false`
   - Configure proper `DATABASE_URL`

2. **Use a production ASGI server**
   ```bash
   uvicorn backend.main:app --host 0.0.0.0 --port 8000 --workers 4
   ```

3. **Use a reverse proxy** (nginx, Apache, etc.)

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Run code quality checks
6. Submit a pull request

