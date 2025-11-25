from fastapi import APIRouter


from app.api.auth import router as auth_router
from app.api.user import router as user_router
from app.api.clinic import router as clinic_router
from app.api.schedule import router as schedule_router
from app.api.patient import router as patient_router
from app.api.appointment import router as appointment_router
from app.api.payment import router as payment_router
from app.api.systempreferences import router as system_preferences_router
 
class APIRouterRegistry:
    """
    Central registry for all API routers.
    """
    def __init__(self):
        self.router = APIRouter()
        self.include_all()

    def include_all(self):
        self.router.include_router(auth_router)
        self.router.include_router(user_router)
        self.router.include_router(clinic_router)
        self.router.include_router(schedule_router)
        self.router.include_router(patient_router)
        self.router.include_router(appointment_router)
        self.router.include_router(payment_router)
        self.router.include_router(system_preferences_router)
api_router_registry = APIRouterRegistry() 
  