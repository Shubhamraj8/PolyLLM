from fastapi import APIRouter
from fastapi.responses import JSONResponse

router = APIRouter()

@router.get("/models")
async def get_models():
    return JSONResponse(content={
        "object": "list",
        "data": [
            {"id": "gpt-4", "object": "model", "owned_by": "gateway"},
            {"id": "gpt-3.5-turbo", "object": "model", "owned_by": "gateway"},
            {"id": "mixtral-8x7b-32768", "object": "model", "owned_by": "groq"},
            {"id": "llama-3.1-8b-instant", "object": "model", "owned_by": "groq"},
            {"id": "gemini-1.5-flash", "object": "model", "owned_by": "gemini"},
            {"id": "gemini-1.5-flash-8b", "object": "model", "owned_by": "gemini"}
        ]
    })
