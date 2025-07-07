from fastapi import FastAPI
from fastapi.responses import JSONResponse

from config import settings

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
)


@app.get("/health")
async def health_check():
    """Health check endpoint for Docker container."""
    return JSONResponse(
        status_code=200,
        content={
            "status": "healthy",
            "service": settings.APP_NAME,
            "version": settings.APP_VERSION,
            "environment": settings.ENVIRONMENT,
        },
    )


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": f"{settings.APP_NAME} Service",
        "status": "running",
        "version": settings.APP_VERSION,
    }


if __name__ == "__main__":
    import uvicorn

    # Log configuration on startup
    settings.log_configuration()

    uvicorn.run(
        app,
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level=settings.LOG_LEVEL.lower(),
    )
