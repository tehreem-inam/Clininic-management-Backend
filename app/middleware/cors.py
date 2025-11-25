from fastapi.middleware.cors import CORSMiddleware
import os
from app.settings import settings

def get_cors_middleware():
    """
    Configure CORS middleware based on environment and frontend requirements.
    Handles your frontend with proper credentials support.
    """
    # Get environment from app settings
    # environment = settings.app_env.lower()
    
    # Base Azure Static Web App origins (your production frontend)
    production_origins = [
        "https://ashy-glacier-0b6fdfa1e.1.azurestaticapps.net",
        "https://www.ashy-glacier-0b6fdfa1e.1.azurestaticapps.net"
    ]
    
    # Development origins (all common localhost ports)
    development_origins = [
        "http://localhost:3000",     # Next.js default
        "http://localhost:3001",     # Alternative Next.js
        "http://localhost:5173",     # Vite default  
        "http://localhost:4200",     # Angular default
        "http://localhost:8000",     # FastAPI default
        "http://localhost:8080",     # Alternative port
        "http://127.0.0.1:3000",
        "http://127.0.0.1:3001", 
        "http://127.0.0.1:5173",
        "http://127.0.0.1:4200",
        "http://127.0.0.1:8000",
        "http://127.0.0.1:8080"
    ]
    
    # Always include both production and development origins for maximum flexibility
    # This allows testing production frontend against local backend and vice versa
    allowed_origins = production_origins + development_origins
    # allowed_origins = (production_origins + development_origins) if environment == "production" else development_origins
    
    # Add additional origins from environment variable if set
    additional_origins = os.getenv("CORS_ORIGINS", getattr(settings, 'cors_origins', ''))
    if additional_origins:
        allowed_origins.extend([origin.strip() for origin in additional_origins.split(",") if origin.strip()])
    
    # Remove duplicates while preserving order
    allowed_origins = list(dict.fromkeys(allowed_origins))
    
    return {
        "middleware_class": CORSMiddleware,
        "options": {
            "allow_origins": allowed_origins,
            "allow_credentials": True,  # Required for your frontend's credentials: 'include'
            "allow_methods": [
                "GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "HEAD"
            ],
            "allow_headers": [
                # Standard headers
                "Accept",
                "Accept-Language", 
                "Content-Language",
                "Content-Type", 
                
                # Authentication (required for your Bearer tokens)
                "Authorization",
                
                # CORS headers your frontend is sending
                "Access-Control-Allow-Origin",
                "Access-Control-Allow-Methods", 
                "Access-Control-Allow-Headers",
                
                # Additional common headers
                "X-Requested-With",
                "X-CSRF-Token",
                "Cache-Control",
                "X-Forwarded-For",
                "X-Forwarded-Proto",
                "Origin",
                "Referer",
                "User-Agent"
            ],
            "expose_headers": [
                # Headers to expose to frontend
                "Content-Type",
                "Authorization", 
                "X-Total-Count",
                "X-Page-Count"
            ],
            "max_age": 3600,  # Cache preflight requests for 1 hour
        }
    }
