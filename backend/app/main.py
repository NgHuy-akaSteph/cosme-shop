"""Main FastAPI application"""

import logging
import os
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, Request, status, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import json

from app.core.config import settings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)


def _sanitize_validation_errors(errors: list[dict]) -> list[dict]:
    """
    Loai bo phan khong JSON-serializable khoi danh sach loi Pydantic.

    Pydantic nhung exception goc vao `ctx["error"]` (vd `ValueError("ID bien the
    bi trung")`) -> `JSONResponse` nem `TypeError` thay vi tra 400. Chi giu lai
    `loc`, `msg`, `type` (de FE hien thi loi) va ep `ctx` ve dang string.
    """
    sanitized: list[dict] = []
    for err in errors:
        item = {
            "loc": [str(p) for p in err.get("loc", ())],
            "msg": err.get("msg", ""),
            "type": err.get("type", ""),
        }
        ctx = err.get("ctx")
        if ctx:
            item["ctx"] = {k: str(v) for k, v in ctx.items()}
        sanitized.append(item)
    return sanitized


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan events.

    Nếu AUTO_MIGRATE=true trong .env, sẽ tự chạy alembic upgrade head
    trước khi start app. Mặc định False để an toàn cho production.
    """
    # Startup
    print("Starting cosme-shop API...")

    if settings.AUTO_MIGRATE:
        try:
            from alembic.config import Config
            from alembic import command

            # Tìm alembic.ini tương ứng với vị trí chạy app
            candidates = ["backend/alembic.ini", "alembic.ini"]
            cfg_path = next((p for p in candidates if os.path.exists(p)), None)
            if cfg_path:
                cfg = Config(cfg_path)
                print(f"Running alembic upgrade head (config={cfg_path})...")
                command.upgrade(cfg, "head")
                print("Migrations applied successfully")
            else:
                print("AUTO_MIGRATE=true but alembic.ini not found, skipping")
        except Exception as exc:
            print(f"AUTO_MIGRATE failed: {exc}")
            # Không raise để app vẫn start được nếu DB đã sẵn sàng

    # Fail-fast khi cau hinh thanh toan sai: app khong start se tot hon
    # de "mat tien im lang" khi giao dich that khong duoc SePay day ve webhook.
    try:
        from app.payment.payment_config_check import check_payment_config

        check_payment_config()
        print("Payment config OK")
    except ValueError as exc:
        print(f"PAYMENT CONFIG INVALID:\n{exc}")
        raise

    yield
    # Shutdown
    print("Shutting down cosme-shop API...")


def create_app() -> FastAPI:
    """Create and configure FastAPI application."""
    app = FastAPI(
        title="Cosme Shop API",
        description="E-commerce API for cosmetics shop",
        version="1.0.0",
        lifespan=lifespan,
    )
    
    # CORS middleware
    try:
        origins = json.loads(settings.CORS_ORIGINS)
    except (json.JSONDecodeError, TypeError):
        origins = ["http://localhost:3000"]
    
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Exception handlers
    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        """Handle Pydantic validation errors."""
        errors = _sanitize_validation_errors(exc.errors())
        first = errors[0] if errors else {}
        msg = first.get("msg", "Dữ liệu không hợp lệ")
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={
                "detail": f"Dữ liệu không hợp lệ: {msg}",
                "message": f"Dữ liệu không hợp lệ: {msg}",
                "code": "VALIDATION_ERROR",
                "errors": errors,
            },
        )
    
    @app.exception_handler(HTTPException)
    async def http_exception_handler(
        request: Request, exc: HTTPException
    ) -> JSONResponse:
        """Handle HTTP exceptions."""
        detail = exc.detail
        if isinstance(detail, dict):
            return JSONResponse(
                status_code=exc.status_code,
                content=detail,
            )
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "detail": str(detail),
                "code": "HTTP_ERROR",
            },
        )
    
    @app.exception_handler(Exception)
    async def general_exception_handler(
        request: Request, exc: Exception
    ) -> JSONResponse:
        """Handle unexpected exceptions."""
        print(f"Unexpected error: {exc}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "detail": "Lỗi server nội bộ",
                "code": "INTERNAL_ERROR",
            },
        )
    
    # Import and include routers
    from app.api.auth import router as auth_router
    from app.api.users import router as users_router
    from app.api.categories import router as categories_router
    from app.api.brands import router as brands_router
    from app.api.products import router as products_router
    from app.api.orders import router as orders_router
    from app.api.admin import router as admin_router
    from app.api.admin_stats import router as admin_stats_router
    from app.api.wishlist import router as wishlist_router
    from app.api.payment import router as payment_router
    from app.api.upload import router as upload_router
    from app.api.coupons import router as coupons_router
    from app.api.coupons import admin_router as admin_coupons_router

    app.include_router(auth_router)
    app.include_router(users_router)
    app.include_router(categories_router)
    app.include_router(brands_router)
    app.include_router(products_router)
    app.include_router(orders_router)
    app.include_router(admin_router)
    app.include_router(admin_stats_router)
    app.include_router(wishlist_router)
    app.include_router(payment_router)
    app.include_router(upload_router)
    app.include_router(coupons_router)
    app.include_router(admin_coupons_router)
    
    # Health check
    @app.get("/health")
    async def health_check():
        return {"status": "ok"}
    
    @app.get("/api")
    async def api_root():
        return {"message": "Cosme Shop API v1.0", "status": "running"}
    
    return app


# Create app instance
app = create_app()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=settings.PORT, reload=True)
