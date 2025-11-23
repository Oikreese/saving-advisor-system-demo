"""
Recommendations API ルート - 互換性ラッパー
フロントエンド 互換性 維持するfor 、簡略化された /recommendations ルート provide
共有コアrecommendationサービス use
"""
from fastapi import APIRouter, HTTPException, Depends, Request
from typing import Optional
import asyncio
from app.services.core.recommendation_service import get_core_recommendation_service, CoreRecommendationService
from app.models.recommendations import RecommendationFeedbackRequest, RegenerationRequest, RecommendationDetail
from app.core.logging import logger

router = APIRouter()


@router.post("/feedback", status_code=204)
async def record_recommendation_feedback(
    request: RecommendationFeedbackRequest,
    core_service: CoreRecommendationService = Depends(get_core_recommendation_service)
):
    """
    recommendationfeedback 記録 - 互換性エンドPoints
    共有コアrecommendationサービス use
    """
    logger.info(f"互換性recommendationfeedbackエンドPoints呼び出し: user_id={request.user_id}, recommendation_id={request.recommendation_id}")
    
    try:
        # コアrecommendationサービス 呼び出し
        result = await core_service.record_recommendation_feedback(request)
        
        if not result.success:
            logger.error(f"recommendationfeedback 処理 failed: {result.error_message}")
            raise HTTPException(status_code=500, detail=result.error_message)
        
        return result.data
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"互換性recommendationfeedback 処理 failed: {e}")
        raise HTTPException(
            status_code=500, 
            detail=f"recommendationfeedback 処理 failed: {str(e)}"
        )


@router.post("/regenerate", response_model=Optional[RecommendationDetail])
async def regenerate_recommendation(
    request: RegenerationRequest,
    core_service: CoreRecommendationService = Depends(get_core_recommendation_service)
):
    """
    recommendationregenerate - 互換性エンドPoints
    共有コアrecommendationサービス use
    """
    logger.info(f"互換性recommendationregenerateエンドPoints呼び出し: user_id={request.user_id}, agent={request.agent_name}")
    
    try:
        # コアrecommendationサービス 呼び出し
        result = await core_service.regenerate_recommendation(request)
        
        if not result.success:
            logger.error(f"recommendation regenerate failed: {result.error_message}")
            raise HTTPException(status_code=500, detail=result.error_message)
        
        return result.data
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"互換性recommendationregenerate 処理 failed: {e}")
        raise HTTPException(
            status_code=500, 
            detail=f"recommendation regenerate failed: {str(e)}"
        )


@router.get("/health")
async def recommendations_health_check(
    core_service: CoreRecommendationService = Depends(get_core_recommendation_service)
):
    """recommendationモジュール ヘルスチェック - コアサービス use"""
    try:
        result = await core_service.health_check()
        
        if result.success:
            return result.data
        else:
            raise HTTPException(status_code=503, detail=result.error_message)
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"recommendationモジュール ヘルスチェック failed: {e}")
        raise HTTPException(status_code=503, detail=f"ヘルスチェック failed: {str(e)}")
