from fastapi import APIRouter

router = APIRouter()


@router.post("/chat/completions")
async def chat_completions():
    pass
