"""Application entry point. Run with: uvicorn app.main:app --reload"""

from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.database import Base, engine
from app.routers import keys, stats, validate


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create the tables on startup if they do not exist yet.
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(
    title="KYC Format Validator",
    description=(
        "Checks whether Indian ID numbers (PAN, Aadhaar, GSTIN, IFSC) are well-formed. "
        "This validates the format and checksum only. It does not confirm that an ID "
        "was actually issued or who it belongs to."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

app.include_router(validate.router)
app.include_router(stats.router)
app.include_router(keys.router)


@app.get("/health", tags=["health"])
def health() -> dict[str, str]:
    return {"status": "ok"}
