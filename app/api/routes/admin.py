from fastapi import APIRouter

router = APIRouter()


@router.post("/reload")
async def reload_config():
    pass
