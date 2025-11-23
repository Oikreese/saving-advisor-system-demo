from fastapi import APIRouter
from app.api.v1.endpoints import (
    assets, tasks, visualization, analysis, analysis_grpc,
    enhanced_recommendations, analytics_sync, monitoring, recommendations_firestore_primary, recommendations,
    debug,  # Debug router
    batch_analytics  # Batch analytics API (替代BigQuery)
)

api_router = APIRouter()

api_router.include_router(assets.router, prefix="/assets", tags=["Assets"])
api_router.include_router(tasks.router, prefix="/tasks", tags=["Tasks"])
api_router.include_router(visualization.router, prefix="/visualization", tags=["Visualization"])
api_router.include_router(analysis.router, prefix="/analysis", tags=["Analysis"])
api_router.include_router(analysis_grpc.router, prefix="/analysis", tags=["Analysis gRPC"])
api_router.include_router(recommendations.router, prefix="/recommendations", tags=["Recommendations"])
api_router.include_router(enhanced_recommendations.router, prefix="/enhanced-recommendations", tags=["Enhanced Recommendations"])
api_router.include_router(recommendations_firestore_primary.router, prefix="/recommendations-firestore-primary", tags=["Recommendations Firestore Primary"])
api_router.include_router(analytics_sync.router, prefix="/analytics-sync", tags=["Analytics Sync"])
api_router.include_router(monitoring.router, prefix="/monitoring", tags=["Monitoring"])
api_router.include_router(batch_analytics.router, prefix="/batch-analytics", tags=["Batch Analytics"])
api_router.include_router(debug.router, prefix="/debug", tags=["Debug"]) # Add the debug router


@api_router.get("/health")
async def health_check():
    """API health check endpoint"""
    return {
        "status": "healthy", 
        "service": "saving_advisor_api",
        "version": "1.0.0"
    }