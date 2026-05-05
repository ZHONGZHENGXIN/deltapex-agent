from contextlib import asynccontextmanager
from time import perf_counter

import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from pydantic import ValidationError

from app.core.config import settings
from app.core.exceptions import http_exception_handler, validation_exception_handler
from app.core.logging import (
    get_logger,
    get_structured_logger,
    get_trace_id,
    reset_trace_id,
    sanitize_trace_id,
    set_trace_id,
    setup_logging,
)
from app.db.base import (
    create_db_and_tables,
    init_default_agent,
    init_default_membership_plans,
    init_default_token_packages,
)
from app.routers.v1.admin import admin_router
from app.routers.v1.auth import auth_router
from app.routers.v1.billing import billing_router
from app.routers.v1.chat import chat_router
from app.routers.v1.membership import membership_router
from app.routers.v1.order import order_router
from app.routers.v1.system import system_router
from app.routers.v1.user import user_router
from app.utils.db import get_redis_client

# 初始化日志系统
setup_logging()
logger = get_logger(__name__)
request_logger = get_structured_logger("app.request")

BASE_PREFIX = "/api/v1"


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("*** 应用程序启动中 ***")
    try:
        # 打印所有环境变量配置
        logger.info("=== 「打印环境变量」开始 ===")
        settings.log_all_settings(logger)
        logger.info("=== 「打印环境变量」完成 ===")

        logger.info("=== 「应用程序初始化」开始 ===")
        # 创建数据库表
        create_db_and_tables()
        # 初始化默认 Agent
        init_default_agent()
        init_default_token_packages()
        # 初始化默认会员计划
        init_default_membership_plans()
        # 初始化 Redis
        app.state.redis = get_redis_client()
        logger.info("=== 「应用程序初始化」完成 ===")
    except Exception as e:
        logger.error(f"应用程序初始化失败: {e}")
        logger.error("程序将终止运行")
        raise  # 重新抛出异常，这将导致 FastAPI 应用启动失败

    yield

    logger.info("*** 应用程序关闭中 ***")
    try:
        if hasattr(app.state, "redis"):
            app.state.redis.close()
            logger.info("Redis 连接已关闭")
    except Exception as e:
        logger.error(f"关闭 Redis 连接时出错: {e}")


app = FastAPI(
    title=settings.API_NAME, 
    version=settings.API_VERSION, 
    lifespan=lifespan,
    docs_url=f"{BASE_PREFIX}/docs",
    redoc_url=f"{BASE_PREFIX}/redoc"
)


@app.middleware("http")
async def trace_id_middleware(request: Request, call_next):
    incoming_trace_id = request.headers.get(settings.TRACE_ID_HEADER) or request.headers.get("X-Request-Id")
    trace_id = sanitize_trace_id(incoming_trace_id)
    trace_token = set_trace_id(trace_id)
    start_time = perf_counter()
    status_code = 500
    error_type = None

    try:
        response = await call_next(request)
        status_code = response.status_code
        response.headers[settings.TRACE_ID_HEADER] = get_trace_id() or trace_id or ""
        return response
    except Exception as exc:
        error_type = type(exc).__name__
        raise
    finally:
        latency_ms = round((perf_counter() - start_time) * 1000, 2)
        log_fields = {
            "method": request.method,
            "path": request.url.path,
            "status_code": status_code,
            "latency_ms": latency_ms,
            "log_hot_retention_days": settings.LOG_HOT_RETENTION_DAYS,
            "log_cold_retention_days": settings.LOG_COLD_RETENTION_DAYS,
        }
        if error_type:
            request_logger.error("request_error", error_type=error_type, **log_fields)
        else:
            request_logger.info("request_complete", **log_fields)
        reset_trace_id(trace_token)


# healthcheck endpoint
@app.get("/health")
def health_check():
    return {"status": "ok"}


# Register exception handlers
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(ValidationError, validation_exception_handler)
app.add_exception_handler(HTTPException, http_exception_handler)

# add CORS support
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(system_router, prefix=BASE_PREFIX, tags=["system"])
app.include_router(auth_router, prefix=BASE_PREFIX, tags=["auth"])
app.include_router(chat_router, prefix=BASE_PREFIX, tags=["chat"])
app.include_router(admin_router, prefix=BASE_PREFIX, tags=["admin"])
app.include_router(user_router, prefix=BASE_PREFIX, tags=["user"])
app.include_router(membership_router, prefix=BASE_PREFIX, tags=["membership"])
app.include_router(order_router, prefix=BASE_PREFIX, tags=["order"])
app.include_router(billing_router, prefix=BASE_PREFIX, tags=["billing"])

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=settings.API_RELOAD,
        reload_dirs=["app"],
    )
