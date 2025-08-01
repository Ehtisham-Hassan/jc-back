from pydantic_settings import BaseSettings
from typing import Optional
import os
from dotenv import load_dotenv

load_dotenv()

class Settings(BaseSettings):
    # API Configuration
    API_V1_STR: str = ""
    PROJECT_NAME: str = "FastAPI Backend"
    VERSION: str = "1.0.0"
    DESCRIPTION: str = "A professional FastAPI backend application"
    

    OPENAI_API_KEY: Optional[str] = None
    OPENAI_MODEL: Optional[str] = None
    # Pinecone Configuration
    PINECONE_API_KEY: Optional[str] = None
    PINECONE_INDEX_NAME: Optional[str] = None
    PINECONE_HOST: Optional[str] = None 

    # Security
    SECRET_KEY: str = "your-secret-key-here-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # Database
    DATABASE_URL: str = "sqlite:///./app.db"
    
    # CORS
    # CORS
    BACKEND_CORS_ORIGINS: list = [
    "https://web-production-813d.up.railway.app", 
    "http://localhost:8080",
    "https://jc-mapping-seven.vercel.app",  # Replace with your actual Vercel domain
    "https://*.vercel.app",  # Allow all Vercel subdomains
    "https://*.railway.app"  # Allow Railway domains too
]
    
    # Environment
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    
    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings() 