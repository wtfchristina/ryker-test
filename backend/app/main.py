from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.routes import router as audit_router

app = FastAPI(
    title="Ryker Room Audit Engine",
    description="Auditor-grade evidence ingestion and continuous attestation platform",
    version="1.0.0",
)

# Enable CORS for client portal frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(audit_router)

@app.get("/health")
async def health_check():
    return {"status": "HEALTHY", "engine": "Ryker Room Core v1"}
