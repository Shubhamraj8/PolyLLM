from fastapi import APIRouter

router = APIRouter()


@router.get("/models")
async def get_models():
    pass
