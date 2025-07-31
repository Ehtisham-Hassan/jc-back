from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.core.config import settings
from backend.core.database import engine, Base
from backend.middleware.cors import add_cors_middleware
from backend.api.endpoint import routes
from backend.models import User


# In src/backend/main.py, add better error handling
@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        # Create database tables
        Base.metadata.create_all(bind=engine)
        print("✅ Database tables created successfully")
        
        # Create superuser
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        db = SessionLocal()
        try:
            from backend.utils.security import get_password_hash
            
            superuser = db.query(User).filter(User.is_superuser == True).first()
            if not superuser:
                superuser = User(
                    email="admin@example.com",
                    username="admin",
                    hashed_password=get_password_hash("admin123"),
                    full_name="Administrator",
                    is_superuser=True,
                    is_active=True
                )
                db.add(superuser)
                db.commit()
                print("✅ Default superuser created: admin@example.com / admin123")
        except Exception as e:
            print(f"⚠️ Error creating superuser: {e}")
        finally:
            db.close()
    except Exception as e:
        print(f"❌ Error during startup: {e}")
        raise e
    
    yield

# @asynccontextmanager
# async def lifespan(app: FastAPI):
#     # Startup
#     # Create database tables
#     Base.metadata.create_all(bind=engine)
    
#     # Create a superuser if it doesn't exist
#     SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
#     db = SessionLocal()
#     try:
#         from backend.utils.security import get_password_hash
        
#         # Check if superuser exists
#         superuser = db.query(User).filter(User.is_superuser == True).first()
#         if not superuser:
#             # Create default superuser
#             superuser = User(
#                 email="admin@example.com",
#                 username="admin",
#                 hashed_password=get_password_hash("admin123"),
#                 full_name="Administrator",
#                 is_superuser=True,
#                 is_active=True
#             )
#             db.add(superuser)
#             db.commit()
#             print("Default superuser created: admin@example.com / admin123")
#     except Exception as e:
#         print(f"Error creating superuser: {e}")
#     finally:
#         db.close()
    
#     yield
    
#     # Shutdown
#     pass


# Create FastAPI app
app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description=settings.DESCRIPTION,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url=f"{settings.API_V1_STR}/docs",
    redoc_url=f"{settings.API_V1_STR}/redoc",
    lifespan=lifespan
)

# Add CORS middleware
add_cors_middleware(app)

# Include routers
app.include_router(routes.router, prefix=settings.API_V1_STR)


@app.get("/")
async def root():
    return {
        "message": "Welcome to FastAPI Backend",
        "version": settings.VERSION,
        "docs": f"{settings.API_V1_STR}/docs"
    }


@app.get("/health")
async def health_check():
    health_status = {
        "status": "healthy",
        "message": "Service is running",
        "version": settings.VERSION,
        "environment": settings.ENVIRONMENT,
        "services": {
            "database": "connected",
            "pinecone": "unknown",
            "openai": "unknown"
        }
    }
    
    # Check Pinecone connection
    try:
        from backend.api.endpoint.db import _get_pinecone_client, _get_openai_client
        _get_pinecone_client()
        health_status["services"]["pinecone"] = "connected"
    except Exception as e:
        health_status["services"]["pinecone"] = f"error: {str(e)}"
        health_status["status"] = "degraded"
    
    # Check OpenAI connection
    try:
        _get_openai_client()
        health_status["services"]["openai"] = "connected"
    except Exception as e:
        health_status["services"]["openai"] = f"error: {str(e)}"
        health_status["status"] = "degraded"
    
    return health_status


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "backend.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )

