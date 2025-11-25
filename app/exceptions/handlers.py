
from fastapi import Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from sqlalchemy.exc import IntegrityError
import logging

logger = logging.getLogger(__name__)

GENERIC_NOTE = "There might be ODBC, SQL, or other API issues. Please check your request and try again."


def build_error_message(msg: str, user_msg: str = None, exc_type: str = None) -> str:
    type_info = f" [ErrorType: {exc_type}]" if exc_type else ""
    if user_msg:
        return f"{user_msg}{type_info} {GENERIC_NOTE}"
    return f"{msg}{type_info} {GENERIC_NOTE}"


def sqlalchemy_integrity_error_handler(request: Request, exc: IntegrityError):
    # Log full exception with traceback for debugging (server-side only)
    logger.exception("SQLAlchemy IntegrityError while handling request %s %s", request.method, request.url)
    msg = str(exc.orig)
    exc_type = type(exc.orig).__name__ if hasattr(exc, 'orig') else type(exc).__name__
    if "duplicate key" in msg or "UNIQUE" in msg or "duplicate" in msg:
        user_msg = "Duplicate or unique constraint violation."
        return JSONResponse(
            status_code=409,
            content={
                "success": False,
                "status_code": 409,
                "message": None,
                "data": None,
                "error": build_error_message(msg, user_msg, exc_type)
            },
        )
    if "IDENTITY_INSERT" in msg:
        user_msg = "Cannot insert explicit value for identity column. Remove explicit ID or check your model."
        return JSONResponse(
            status_code=400,
            content={
                "success": False,
                "status_code": 400,
                "message": None,
                "data": None,
                "error": build_error_message(msg, user_msg, exc_type)
            },
        )
    user_msg = "Database integrity error."
    return JSONResponse(
        status_code=400,
        content={
            "success": False,
            "status_code": 400,
            "message": None,
            "data": None,
            "error": build_error_message(msg, user_msg, exc_type)
        },
    )


def validation_error_handler(request: Request, exc: RequestValidationError):
    """Handle FastAPI validation errors with detailed field information"""
    errors = []
    for error in exc.errors():
        field = " -> ".join([str(loc) for loc in error["loc"][1:]])  # Skip 'body'
        message = error["msg"]
        errors.append(f"{field}: {message}" if field else message)
    
    error_msg = "Validation failed: " + "; ".join(errors)
    
    return JSONResponse(
        status_code=422,
        content={
            "success": False,
            "status_code": 422,
            "message": None,
            "data": None,
            "error": error_msg
        },
    )


def generic_exception_handler(request: Request, exc: Exception):
    user_msg = "Internal server error."
    exc_type = type(exc).__name__
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "status_code": 500,
            "message": None,
            "data": None,
            "error": build_error_message(str(exc), user_msg, exc_type)
        },
    )
