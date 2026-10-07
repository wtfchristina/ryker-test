from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from app.api.routes import router as audit_router

app = FastAPI(
    title="Ryker Room Audit Engine",
    description="Auditor-grade evidence ingestion and continuous attestation platform",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(audit_router)

@app.get("/portal", include_in_schema=False)
async def serve_portal():
    return FileResponse("app/static/index.html")

@app.get("/health", tags=["default"])
async def health_check():
    return {"status": "HEALTHY", "engine": "Ryker Room Core v1"}
