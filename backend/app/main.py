from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_router
from app.core.config import settings
from app.mcp.server import mcp_app


def create_application() -> FastAPI:
    # The MCP server owns the session-manager lifecycle (see app/mcp/server.py);
    # FastAPI must run it as its own lifespan or the streamable-HTTP transport
    # never initializes.
    application = FastAPI(
        title=settings.app_name,
        debug=settings.debug,
        lifespan=mcp_app.router.lifespan_context,
    )
    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.get_cors_origins(),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    application.include_router(api_router, prefix=settings.api_v1_prefix)
    application.mount("/mcp", mcp_app)
    return application


app = create_application()
