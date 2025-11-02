from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.logging import setup_logging
from app.middleware.request_id import request_id_middleware
from app.routers import completions, health, admin, feedback

app = FastAPI(
    title="AI Code Completion Server", 
    version="1.0.0",
    description="Personalized AI code completion with user profiling"
)
setup_logging()
# set up logging va middleware request_id
app.middleware("http")(request_id_middleware)

origins = (
    [o.strip() for o in settings.ALLOW_ORIGINS.split(",")] if settings.ALLOW_ORIGINS else ["*"]
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(completions.router)
app.include_router(admin.router)
app.include_router(feedback.router)
