from fastapi import APIRouter, HTTPException, status
from app.schemas.chat import ChatRequest, ChatResponse
router = APIRouter(tags=["Chat"])

@router.post("/chat", response_model=ChatResponse)
def chat_endpoint(payload: ChatRequest):
    """TODO: implement RAG pipeline (retrieval + generation)."""
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Chat/RAG pipeline not implemented yet.",
    )
