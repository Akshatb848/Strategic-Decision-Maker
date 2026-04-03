from .health import router as health_router
from .analysis import router as analysis_router
from .reports import router as reports_router
from .auth import router as auth_router

__all__ = ["health_router", "analysis_router", "reports_router", "auth_router"]
