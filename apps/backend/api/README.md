# FastAPI Application Foundation

This directory contains the FastAPI application foundation for the R.E.M.I Backend.

## Structure

```
api/
├── __init__.py           # Package initialization
├── dependencies.py       # Dependency injection functions
├── README.md            # This file
└── routes/              # API endpoint routers
    ├── __init__.py      # Routes package initialization
    └── health.py        # Health check endpoints
```

## Components

### Main Application (`main.py`)

The main FastAPI application with:
- **Lifespan Management**: Handles startup/shutdown events
- **CORS Middleware**: Configured for allowed origins
- **API Routing**: Includes all route modules
- **OpenAPI Documentation**: Available at `/docs` and `/redoc`
- **Global Exception Handler**: Catches unhandled errors

### Dependencies (`dependencies.py`)

Reusable dependency injection functions:
- `get_database_session()`: Provides async database sessions
- `get_settings()`: Provides application settings
- `get_pagination_params()`: Provides pagination parameters
- `validate_uuid()`: Validates UUID format

### Health Check Routes (`routes/health.py`)

Health monitoring endpoints:
- `GET /api/v1/health`: Basic health check
- `GET /api/v1/health/detailed`: Detailed component health
- `GET /api/v1/health/database`: Database health check
- `GET /api/v1/health/redis`: Redis health check (TODO)
- `GET /api/v1/health/stages/{stage}`: Stage-specific health (TODO)
- `GET /api/v1/stats`: System statistics

## Running the Application

### Development Mode

```bash
# Using main.py
python main.py

# Using uvicorn directly
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### Production Mode

```bash
# Set environment to production
export ENV=production
export DEBUG=false

# Run with multiple workers
uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4
```

## API Documentation

Once the application is running, access the documentation at:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **OpenAPI JSON**: http://localhost:8000/openapi.json

## Health Checks

### Basic Health Check

```bash
curl http://localhost:8000/api/v1/health
```

Response:
```json
{
  "status": "healthy",
  "timestamp": "2024-01-01T12:00:00.000000",
  "version": "1.0.0",
  "environment": "development"
}
```

### Detailed Health Check

```bash
curl http://localhost:8000/api/v1/health/detailed
```

Response:
```json
{
  "status": "healthy",
  "timestamp": "2024-01-01T12:00:00.000000",
  "version": "1.0.0",
  "environment": "development",
  "components": [
    {
      "name": "database",
      "status": "healthy",
      "message": "Database is responsive",
      "latency_ms": 5.23
    }
  ]
}
```

## Adding New Routes

1. Create a new router file in `routes/`:

```python
# routes/my_feature.py
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from api.dependencies import get_database_session

router = APIRouter()

@router.get("/my-endpoint")
async def my_endpoint(db: AsyncSession = Depends(get_database_session)):
    return {"message": "Hello from my feature"}
```

2. Import and include the router in `main.py`:

```python
from api.routes import health, my_feature

app.include_router(my_feature.router, prefix="/api/v1", tags=["My Feature"])
```

## Using Dependencies

### Database Session

```python
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from api.dependencies import get_database_session

@router.get("/items")
async def get_items(db: AsyncSession = Depends(get_database_session)):
    result = await db.execute(select(Item))
    return result.scalars().all()
```

### Pagination

```python
from fastapi import Depends
from api.dependencies import get_pagination_params, PaginationParams

@router.get("/items")
async def list_items(
    pagination: PaginationParams = Depends(get_pagination_params)
):
    return {
        "skip": pagination.skip,
        "limit": pagination.limit
    }
```

### Settings

```python
from fastapi import Depends
from config.config import Settings
from api.dependencies import get_settings

@router.get("/config")
async def get_config(settings: Settings = Depends(get_settings)):
    return {"environment": settings.ENV}
```

## CORS Configuration

CORS is configured in `main.py` using the `CORS_ORIGINS` setting from `config.py`.

To add allowed origins, update your `.env` file:

```env
CORS_ORIGINS=["http://localhost:3000", "http://localhost:8080", "https://myapp.com"]
```

## Error Handling

The application includes a global exception handler that:
- Logs all unhandled exceptions
- Returns structured error responses
- Includes error details in debug mode
- Hides sensitive information in production

## Next Steps

- [ ] Implement Redis health check
- [ ] Add authentication dependencies
- [ ] Create connection management routes
- [ ] Add collection endpoints
- [ ] Implement message routes
- [ ] Add AI processing endpoints
