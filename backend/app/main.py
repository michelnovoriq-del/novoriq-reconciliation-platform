import logging
import time
import uuid

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse

from app.config import Settings, get_settings
from app.routes import account, auth, billing, files, health, match_results, reconciliation_runs, webhooks


logger = logging.getLogger(__name__)


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    application = FastAPI(
        title="Novoriq Reconciliation Agent API",
        version="0.1.0",
        description="CSV/Excel reconciliation workflows.",
        debug=settings.debug,
        docs_url=None if settings.is_production else "/docs",
        redoc_url=None if settings.is_production else "/redoc",
        openapi_url=None if settings.is_production else "/openapi.json",
    )

    application.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.trusted_hosts)

    @application.middleware("http")
    async def production_http_safety(request: Request, call_next):
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        started = time.monotonic()
        try:
            response = await call_next(request)
        except Exception:
            logger.exception("Unhandled request error request_id=%s route=%s", request_id, request.url.path)
            response = JSONResponse(
                status_code=500,
                content={"detail": {"code": "INTERNAL_ERROR", "message": "An unexpected error occurred.", "request_id": request_id}},
            )
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Content-Security-Policy"] = "default-src 'none'; frame-ancestors 'none'"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        if settings.is_production:
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        logger.info("request request_id=%s method=%s route=%s status=%s duration_ms=%d", request_id, request.method, request.url.path, response.status_code, (time.monotonic() - started) * 1000)
        return response

    application.include_router(health.router)
    application.include_router(auth.router)
    application.include_router(account.router)
    application.include_router(billing.router)
    application.include_router(files.router)
    application.include_router(reconciliation_runs.router)
    application.include_router(match_results.router)
    application.include_router(webhooks.router)

    @application.on_event("startup")
    def validate_production_configuration() -> None:
        settings.validate_production()
        if settings.is_production:
            settings.validate_whop_startup()

    # Add CORS last so it remains the outermost layer and annotates safe error responses.
    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=False,  # Authentication is Authorization bearer-token based.
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Accept", "Authorization", "Content-Type", "X-CSRF-Token", "X-Request-ID"],
        expose_headers=["X-Request-ID"],
        max_age=600,
    )
    return application


app = create_app()
