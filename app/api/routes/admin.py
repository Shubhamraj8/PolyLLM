from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from loguru import logger

from app.dependencies import get_config_loader

router = APIRouter()


@router.post("/reload")
async def reload_config(config_loader=Depends(get_config_loader)):
    await config_loader.reload()
    timestamp = datetime.now(timezone.utc).isoformat()
    return JSONResponse(content={"status": "reloaded", "timestamp": timestamp})
