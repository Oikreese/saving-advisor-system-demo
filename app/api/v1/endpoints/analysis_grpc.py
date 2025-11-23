"""
Analysis模块的gRPC版本endpoint - already重构为use共享core service
这个endpoint现在直接调用核心analysis service，避免in部gRPC网络调用开销
"""
from fastapi import APIRouter, HTTPException, Depends
from app.services.core.analysis_service import get_core_analysis_service, CoreAnalysisService
from app.core.logging import logger

router = APIRouter()


@router.get("/general-grpc/{user_id}", response_model=str)
async def get_general_analysis_grpc(
    user_id: str,
    core_service: CoreAnalysisService = Depends(get_core_analysis_service)
):
    """
    getuser的总体portfolioanalysis - use共享core service
    optimized：直接调用core service，避免in部网络调用开销
    """
    logger.info(f"analysisgRPCendpoint调用: user_id={user_id}")
    
    try:
        # 调用核心analysis service（无网络开销）
        result = await core_service.analyze_general_portfolio(user_id, allow_empty_portfolio=False)
        
        if not result.success:
            logger.error(f"analysisfail: {result.error_message}")
            raise HTTPException(status_code=500, detail=result.error_message)
        
        logger.info(f"analysissuccess: user_id={user_id}")
        return result.analysis_summary
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"analysis service调用fail: user_id={user_id}, error={e}")
        raise HTTPException(
            status_code=500, 
            detail=f"analysis service调用fail: {str(e)}"
        )


@router.get("/health-grpc")
async def grpc_health_check(
    core_service: CoreAnalysisService = Depends(get_core_analysis_service)
):
    """analysis servicehealth checkendpoint - usecore service"""
    try:
        # testcore serviceconnected
        result = await core_service.analyze_general_portfolio("health_check_user", allow_empty_portfolio=True)
        
        # 即使user不存在，core service应该能正常response
        status = "healthy"
        message = "analysiscore service正常run"
        
        return {
            "status": status,
            "service": "analysis_core_service",
            "message": message,
            "architecture": "shared_core_service",
            "performance": "optimized_no_network_overhead"
        }
        
    except Exception as e:
        logger.error(f"analysis servicehealth checkfail: {e}")
        raise HTTPException(
            status_code=503,
            detail=f"analysis serviceunavailable: {str(e)}"
        )
