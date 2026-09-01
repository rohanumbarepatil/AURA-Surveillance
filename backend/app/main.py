from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
import os
from .routers import cameras, events, rules, snapshots, sandbox
from .websocket_manager import router as websocket_router
from .database import init_db

app = FastAPI(
    title="AURA Surveillance API",
    version="0.1.0",
)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://aura-surveillance.vercel.app"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(cameras.router)
app.include_router(events.router)
app.include_router(rules.router)
app.include_router(snapshots.router)
app.include_router(sandbox.router)
app.include_router(websocket_router)

@app.on_event("startup")
def startup():
    init_db()


@app.get("/api/health")
def health_check():
    return {
        "status": "ok",
        "service": "AURA Surveillance API",
        "version": "0.1.0",
    }

# Ensure frontend directory exists before mounting
frontend_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "frontend")
if not os.path.exists(frontend_path):
    os.makedirs(frontend_path)

# Serve static frontend files
app.mount("/", StaticFiles(directory=frontend_path, html=True), name="frontend")
