from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.app.routers import chat
from backend.app.config import get_settings
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)
settings = get_settings()

app = FastAPI(
    title="MCP DataOps Backend",
    version="1.0.0",
    description="Backend API for MCP-based DataOps Assistant"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(chat.router)


@app.get("/")
def root():
    return {
        "service": "MCP DataOps Backend",
        "version": "1.0.0",
        "status": "healthy",
        "environment": settings.environment
    }


@app.get("/health")
def health():
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
