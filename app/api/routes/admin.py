from datetime import UTC, datetime

from fastapi import APIRouter, Depends, Security
from fastapi.responses import JSONResponse

from app.dependencies import get_api_key, get_config_loader

router = APIRouter()


@router.post("/reload")
async def reload_config(
    api_key: str = Security(get_api_key),
    config_loader=Depends(get_config_loader),
):
    await config_loader.reload()
    timestamp = datetime.now(UTC).isoformat()
    return JSONResponse(content={"status": "reloaded", "timestamp": timestamp})
