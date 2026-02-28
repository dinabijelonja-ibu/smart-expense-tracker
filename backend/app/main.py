from fastapi import FastAPI

from app.api.v1.router import api_router
from app.core.config import settings


def create_application() -> FastAPI:
    application = FastAPI(title=settings.app_name, debug=settings.debug)
    application.include_router(api_router, prefix=settings.api_v1_prefix)
    return application


app = create_application()
