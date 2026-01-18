import uvicorn
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from config import settings
from services.db.postgres_connector import database_service
from services.object_store.minio_connector import get_minio_connector
from api.v1.api import api_router

from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware

app = FastAPI(
    title="Claire API",
    description="API for the Claire project",
    version="0.1.0",
)

# Trust all proxies (Railway/Vercel/etc handling SSL termination)
app.add_middleware(ProxyHeadersMiddleware, trusted_hosts=["*"])

allowed_origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "https://claire-snowy.vercel.app",  # Production Vercel frontend
]

if settings.BACKEND_API_ENVIRONMENT == "production":
    pass

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix=settings.BACKEND_API_V1_STR)

@app.get("/", tags=["Monitoring"])
async def root(request: Request):
    """Root endpoint returning basic API information."""
    return {
        'name': settings.BACKEND_PROJECT_NAME,
        'description': settings.BACKEND_API_DESCRIPTION,
        'version': settings.BACKEND_API_VERSION,
        'environment': settings.BACKEND_API_ENVIRONMENT,
        'status': 'healthy',
        'swagger_url': '/docs',
        'redoc_url': '/redoc',
    }

@app.get("/services_health", tags=["Monitoring"])
async def health_check(request: Request):
    """Services Health check endpoint."""
    try:
        db_health = await database_service.health_check()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database health check failed: {str(e)}")

    try:
        minio_connector = get_minio_connector()
        minio_health = minio_connector.health_check()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"MinIO health check failed: {str(e)}")
    return {
        "status": "healthy",
        "database": "healthy" if db_health else "unhealthy",
        "minio": "healthy" if minio_health else "unhealthy",
    }

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)