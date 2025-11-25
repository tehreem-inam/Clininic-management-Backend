# app/main.py

from fastapi import FastAPI , Request
import logging
import socket
import os
from app.settings import settings
from fastapi.exception_handlers import RequestValidationError
from fastapi.exceptions import RequestValidationError
from sqlalchemy.exc import IntegrityError
from app.exceptions.handlers import sqlalchemy_integrity_error_handler, generic_exception_handler, validation_error_handler
from app.middleware.cors import get_cors_middleware
from app.router.routes import api_router_registry
from app.database import init_db
import asyncio
import sys

if sys.platform.startswith("win"):
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())


app = FastAPI(title="Clinic Management Backend API", version="0.0.2")

#Enable CORS middleware
cors_config = get_cors_middleware()
app.add_middleware(
    cors_config["middleware_class"],
    **cors_config["options"]
)



#Register global exception handlers
app.add_exception_handler(RequestValidationError, validation_error_handler)
app.add_exception_handler(IntegrityError,sqlalchemy_integrity_error_handler)
app.add_exception_handler(Exception, generic_exception_handler)

#Root route: health check and available routes
@app.get("/")
def root(request: Request):
    routes = []
    for route in app.routes:
        if hasattr(route,'path') and hasattr(route,'methods'):
            routes.append({
                "path": route.path,
                "methods": list(route.methods)
            })
    return{
        "status":"OK",
        "message":"Backend is running",
        "available_routes": routes
    }
#Attach all API routers
app.include_router(api_router_registry.router)

def _get_local_ips() -> list[str]:
    ips: set[str] = set()
    # Attempt to discover primary outbound IP
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        # doesn't actually send data
        s.connect(("8.8.8.8", 80))
        ips.add(s.getsockname()[0])
        s.close()
    except Exception:
        pass

    # Try hostname resolution which may list additional addresses
    try:
        hostname = socket.gethostname()
        for ip in socket.gethostbyname_ex(hostname)[2]:
            ips.add(ip)
    except Exception:
        pass

    # Fallback to localhost if nothing found
    if not ips:
        return ["127.0.0.1"]

    # Prefer non-loopback addresses; if none, return whatever we have
    non_loop = [ip for ip in ips if not ip.startswith("127.")]
    return non_loop or list(ips)

# @app.on_event("startup")
# async def startup_event():
#     await init_db()  # auto-creates tables
@app.on_event("startup")
async def _log_startup_access_urls() -> None:
    """Log local network IP(s) and suggested access URLs so a device on the same router can connect."""
    logger = logging.getLogger("uvicorn.error")
    try:
        await init_db()  # auto-creates tables
        ips = _get_local_ips()
        # Determine port preference: settings.app_port, then PORT env, then 8000
        port = os.getenv("PORT") or getattr(settings, "app_port", None) or 8000
        for ip in ips:
            logger.info("Server reachable on local network: http://%s:%s/ (use this IP from devices on the same router)", ip, port)
        # Also log localhost for convenience
        logger.info("Local access: http://127.0.0.1:%s/", port)
    except Exception:
        logger.exception("Failed to detect local IPs for startup logging")
   