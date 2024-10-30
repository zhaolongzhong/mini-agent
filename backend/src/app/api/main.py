from fastapi import APIRouter

from app.api.routes import messages, assistants, conversations, assistant_memory

api_router = APIRouter()

# Update the router registrations
api_router.include_router(assistants.router, prefix="/assistants", tags=["assistants"])

api_router.include_router(
    assistant_memory.router,
    prefix="/assistants",
    tags=["assistant_memory"],
)

api_router.include_router(conversations.router, prefix="/conversations", tags=["conversations"])

api_router.include_router(messages.router, prefix="/messages", tags=["messages"])
