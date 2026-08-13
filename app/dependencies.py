from fastapi import Depends, HTTPException, Security
from fastapi.security import APIKeyHeader
from starlette.requests import Request

from app.config.settings import Settings

api_key_header = APIKeyHeader(name="X-API-Key")


def get_settings(request: Request) -> Settings:
    return request.app.state.settings


def get_redis(request: Request):
    return request.app.state.redis


def get_config_loader(request: Request):
    return request.app.state.config_loader


def get_router(request: Request):
    return request.app.state.router


def get_rate_limiter(request: Request):
    return request.app.state.rate_limiter


def get_audit_logger(request: Request):
    return request.app.state.audit_logger


def get_cost_tracker(request: Request):
    return request.app.state.cost_tracker


def get_api_key(
    api_key: str = Security(api_key_header),
    settings: Settings = Depends(get_settings),
) -> str:
    if api_key != settings.gateway_api_key:
        raise HTTPException(status_code=401, detail="Invalid API Key")
    return api_key
