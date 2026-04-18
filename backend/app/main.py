import os
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE" # Prevent OpenMP double initialization crash on Windows when using Faiss+Torch
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware

from app.config import settings
from app.database import check_db_connection
from app.routes import upload, chat, summary, auth
from app.services.redis_service import rate_limit_middleware, get_redis

# ── App ───────────────────────────────────────────────────────────────────
app = FastAPI(
    title="AI-Powered Document & Multimedia Q&A",
    description="Upload PDFs, audio, and video → ask questions → get AI answers with timestamps.\n\n"
                "**Auth:** Register → Login → Use Bearer token for protected endpoints.",
    version="1.0.0",
    docs_url="/docs",        # Swagger UI at http://localhost:8000/docs
    redoc_url="/redoc",
)

# ── CORS (allow React dev server) ─────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost",
        "http://127.0.0.1",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-RateLimit-Limit", "X-RateLimit-Remaining", "X-RateLimit-Reset"],
)

# ── Rate Limiter Middleware (Redis-backed) ────────────────────────────────
app.add_middleware(BaseHTTPMiddleware, dispatch=rate_limit_middleware)

# ── Static file serving for uploaded media (Play button needs this) ───────
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
app.mount("/media", StaticFiles(directory=settings.UPLOAD_DIR), name="media")

# ── Routes ────────────────────────────────────────────────────────────────
app.include_router(auth.router,    prefix="/api", tags=["Auth"])
app.include_router(upload.router,  prefix="/api", tags=["Upload"])
app.include_router(chat.router,    prefix="/api", tags=["Chat"])
app.include_router(summary.router, prefix="/api", tags=["Summary"])


# ── Startup ───────────────────────────────────────────────────────────────
@app.on_event("startup")
async def startup_event():
    check_db_connection()
    os.makedirs(settings.FAISS_DIR, exist_ok=True)
    get_redis()  # Warm up Redis connection (non-blocking, won't crash if down)
    print("Server started. Swagger docs at http://localhost:8000/docs")


@app.get("/")
async def root():
    return {"message": "AI Q&A API is running 🚀", "docs": "/docs"}


@app.get("/health")
async def health():
    return {"status": "ok"}
