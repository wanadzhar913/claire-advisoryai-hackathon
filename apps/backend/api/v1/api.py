from fastapi import APIRouter

from services.db.postgres_connector import DatabaseService
from api.v1 import (
    file_uploads,
    users,
    query_transactions,
    chatbot,
    goals,
    insights
)

api_router = APIRouter()

# Include routers
api_router.include_router(users.router, prefix="/users", tags=["Users"])
api_router.include_router(file_uploads.router, prefix="/file-uploads", tags=["File Uploads"])
api_router.include_router(query_transactions.router, prefix="/query", tags=["Query Financial Transactions"])
api_router.include_router(chatbot.router, prefix="/chatbot", tags=["Financial Advice Agent"])
api_router.include_router(goals.router, prefix="/goals", tags=["Goals"])
api_router.include_router(insights.router, prefix="/insights", tags=["Financial Insights"])

@api_router.get("/app_health", tags=["Monitoring"])
async def app_health_check():
    """App health check endpoint.

    Returns:
        dict: App health status information.
    """
    return {"status": "healthy", "version": "1.0.0"}