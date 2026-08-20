from datetime import UTC, datetime

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

from app.dependencies import get_config_loader

router = APIRouter()


@router.post("/reload")
async def reload_config(config_loader=Depends(get_config_loader)):
    await config_loader.reload()
    timestamp = datetime.now(UTC).isoformat()
    return JSONResponse(content={"status": "reloaded", "timestamp": timestamp})
