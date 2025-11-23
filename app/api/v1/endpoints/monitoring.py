"""
API Endpoint for Real-time System Monitoring
"""
import asyncio
import json
from datetime import datetime
from fastapi import APIRouter, Depends, Request
from sse_starlette.sse import EventSourceResponse

from app.services.monitoring_service import MonitoringService, get_monitoring_service
from app.core.logging import logger
from app.core.config import settings

router = APIRouter()

# 全局变量trackSSEconnected数，防止过多connected导致system过载
_active_sse_connections = 0
_max_sse_connections = 5  # 最多允许5个并发monitorconnected

@router.get("/status-stream")
async def status_stream(
    request: Request,
    monitoring_service: MonitoringService = Depends(get_monitoring_service)
):
    """
    Streams real-time system performance metrics using Server-Sent Events (SSE).
    """
    global _active_sse_connections
    
    # checkwhetherenabledSSEmonitor
    if not settings.ENABLE_SSE_MONITORING:
        logger.info("SSEmonitordisabled")
        return EventSourceResponse(
            iter([{"event": "disabled", "data": json.dumps({"message": "SSE monitoring is disabled"})}])
        )
    
    # checkconnected数限制
    if _active_sse_connections >= _max_sse_connections:
        logger.warning(f"SSEconnected数already达上限 ({_max_sse_connections})，拒绝newconnected")
        return EventSourceResponse(
            iter([{"event": "error", "data": json.dumps({"error": "Too many monitoring connections"})}])
        )
    
    async def event_generator():
        global _active_sse_connections
        _active_sse_connections += 1
        logger.info(f"newSSEconnected建立，currentconnected数: {_active_sse_connections}")
        
        try:
            while True:
                # If client closes connection, stop sending events
                if await request.is_disconnected():
                    logger.info("Monitoring client disconnected.")
                    break

                try:
                    metrics = await monitoring_service.get_system_metrics()
                    yield {
                        "event": "update",
                        "data": json.dumps(metrics)
                    }
                except Exception as e:
                    logger.error(f"Error getting system metrics: {e}")
                    yield {
                        "event": "error",
                        "data": json.dumps({"error": "Failed to fetch metrics"})
                    }

                # 增加updateinterval以reduce资源消耗
                await asyncio.sleep(3)  # 3秒updateinterval，平衡performanceand实时性
        
        finally:
            # connectedend时reduce计数
            _active_sse_connections -= 1
            logger.info(f"SSEconnecteddisconnected，剩余connected数: {_active_sse_connections}")

    return EventSourceResponse(event_generator())

@router.post("/deep-check")
async def perform_deep_check(
    monitoring_service: MonitoringService = Depends(get_monitoring_service)
):
    """
    Performs comprehensive system health checks including business logic tests.
    This endpoint is designed for on-demand deep analysis and may take longer to complete.
    """
    try:
        results = await monitoring_service.perform_deep_checks()
        return results
    except Exception as e:
        logger.error(f"Error performing deep checks: {e}")
        return {
            "error": "Failed to perform deep checks",
            "details": str(e),
            "timestamp": datetime.now().isoformat()
        }
