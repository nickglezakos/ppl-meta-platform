from fastapi import FastAPI
from fastapi.responses import JSONResponse

app = FastAPI(title="PPL Meta Orchestrator", version="1.0.0")


@app.get("/health")
async def health_check():
    """Health check endpoint for Docker container."""
    return JSONResponse(
        status_code=200,
        content={
            "status": "healthy",
            "service": "ppl-meta-orchestrator",
            "version": "1.0.0",
        },
    )


@app.get("/")
async def root():
    """Root endpoint."""
    return {"message": "PPL Meta Orchestrator Service", "status": "running"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8002)
