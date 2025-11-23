from fastapi import APIRouter, HTTPException, Depends
from typing import List
from datetime import datetime
from app.core.logging import logger
from app.services.firestore.firestore_primary_service import get_firestore_primary_service, FirestorePrimaryService
from app.models.assets import UserPortfolio
from app.models.recommendations import (
    ComprehensiveRecommendation, MonthlyTaskList, 
    FinalizeSessionRequest, MultiAgentResponse
)
from app.agents.multi_agent_system import multi_agent_system
from app.services.utils.task_service import TaskService

router = APIRouter()
task_service = TaskService()

@router.get("/recommendations/preview/{user_id}", response_model=MultiAgentResponse)
async def get_recommendations_preview(user_id: str, firestore_service: FirestorePrimaryService = Depends(get_firestore_primary_service)):
    """
    recommendations プレビュー 取得（user 受諾前 確認用）
    """
    logger.info(f"recommendationsプレビュー取得: user_id={user_id}")
    try:
        portfolio = await firestore_service.get_user_portfolio(user_id, allow_empty=False, raise_http_exception=True)
        
        response = await multi_agent_system.analyze_portfolio(portfolio)
        
        logger.info(f"generateされた推奨プレビュー: user_id={user_id}")
        return response
    
    except Exception as e:
        logger.error(f"recommendationsプレビュー取得エラー: {e}")
        raise HTTPException(status_code=500, detail="recommendationsプレビュー 取得 failed")

@router.post("/session/finalize", status_code=204)
async def finalize_session(request: FinalizeSessionRequest, firestore_service: FirestorePrimaryService = Depends(get_firestore_primary_service)):
    """
    user feedback AIセッション 最終処理
    """
    logger.info(f"セッション最終処理: user_id={request.user_id}")
    try:
        # Convert ai_response from List to Dict for save_ai_session
        ai_response_dict = {
            "recommendations": request.ai_response,
            "total_count": len(request.ai_response)
        }
        
        await firestore_service.save_ai_session(
            user_id=request.user_id,
            session_type=request.session_type,
            input_data=request.input_data,
            ai_response=ai_response_dict,
            processing_time_ms=request.processing_time_ms,
            user_feedback=request.feedback
        )
        logger.info(f"セッションsavesuccess: user_id={request.user_id}")
        return
    except Exception as e:
        logger.error(f"セッション最終処理エラー: {e}")
        raise HTTPException(status_code=500, detail="セッション save failed")

@router.post("/comprehensive/{user_id}", response_model=ComprehensiveRecommendation)
async def get_comprehensive_recommendation(user_id: str, request: dict, firestore_service: FirestorePrimaryService = Depends(get_firestore_primary_service)):
    logger.info(f"包括 なrecommendations取得: user_id={user_id}")
    try:
        accepted_ids = request.get("accepted_recommendation_ids", [])
        
        # user assetportfolio 取得
        portfolio = await firestore_service.get_user_portfolio(user_id, allow_empty=False, raise_http_exception=True)
        
        # 適切なメソッド 呼び出して総合 なrecommendation generate
        comprehensive_rec = await TaskService.generate_comprehensive_recommendation(
            user_id=user_id,
            portfolio=portfolio,
            asset_recommendations=[],  # 空 list 渡すこ   き、メソッドin部 処理されます
            accepted_recommendation_ids=accepted_ids
        )

        return comprehensive_rec
    except Exception as e:
        logger.error(f"包括 なrecommendations取得エラー: {e}")
        raise HTTPException(status_code=500, detail="包括 なrecommendations 取得 failed")

@router.post("/monthly/{user_id}", response_model=MonthlyTaskList)
async def get_monthly_tasks(
    user_id: str, 
    request: dict,
    firestore_service: FirestorePrimaryService = Depends(get_firestore_primary_service)
):
    """
    user 受け入れたrecommendations based on、パーソナライズされたmonth間タスクlist generateします。
    """
    logger.info(f"パーソナライズされたmonth間タスクlist generate開始: user_id={user_id}")
    try:
        accepted_recommendation_ids = request.get("accepted_recommendation_ids", [])
        if not accepted_recommendation_ids:
            raise HTTPException(status_code=400, detail="受け入れられたrecommendationsID provideされていません。")

        # userportfolio 取得
        portfolio = await firestore_service.get_user_portfolio(user_id, allow_empty=False, raise_http_exception=True)
        
        # 包括 なrecommendations generate
        comprehensive_rec = await TaskService.generate_comprehensive_recommendation(
            user_id=user_id,
            portfolio=portfolio,
            asset_recommendations=[],  # こ context  空 問題not available
            accepted_recommendation_ids=accepted_recommendation_ids
        )
        
        # パーソナライズされたタスク generate
        monthly_tasks = await TaskService.generate_monthly_tasks(
            user_id=user_id,
            comprehensive_recommendation=comprehensive_rec
        )
        
        logger.info(f"パーソナライズされたmonth間タスクlist generatesuccess: user_id={user_id}")
        return monthly_tasks
        
    except HTTPException as http_exc:
        logger.error(f"HTTPエラー - month間タスクlist取得中: {http_exc.detail}")
        raise
    except Exception as e:
        logger.error(f"month間タスクlist取得エラー: {e}")
        raise HTTPException(status_code=500, detail="month間タスクlist 取得 failed")
