"""
analysis同期サービスAPIエンドPoints

BigQuery from Firestoreへ data同期タスク 監視 管理
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks
from typing import Dict, Any
from datetime import datetime
import logging

# 同期タスク 現在sync_starter よって統一管理されています
from app.core.config import settings
from app.core.logging import logger

router = APIRouter()


@router.get("/status")
async def get_analytics_sync_status() -> Dict[str, Any]:
    """analysis同期サービス 状態 取得"""
    try:
        from app.services.utils.service_manager import unified_service_manager
        
        if not settings.ENABLE_ANALYTICS_SYNC:
            return {
                "status": "success",
                "sync_services": {
                    "services_started": False,
                    "sync_enabled": False,
                    "initial_sync_enabled": False,
                    "health": {
                        "healthy": False,
                        "message": "analysis同期サービス 無効化されています"
                    }
                },
                "message": "analysis同期サービス 無効化されています",
                "checked_at": datetime.now().isoformat()
            }
        
        # サービス状態 取得
        service_status = await unified_service_manager.get_service_status('analytics_sync')
        
        # 戻りdata build
        is_running = service_status.get('status') == 'running'
        worker_running = service_status.get('worker_running', False)
        beat_running = service_status.get('beat_running', False)
        
        return {
            "status": "success",
            "sync_services": {
                "services_started": is_running,
                "worker_pid": service_status.get('worker_pid'),
                "beat_pid": service_status.get('beat_pid'),
                "sync_enabled": settings.ENABLE_ANALYTICS_SYNC,
                "initial_sync_enabled": settings.INITIAL_SYNC_ON_STARTUP,
                "configuration": {
                    "batch_size": settings.SYNC_BATCH_SIZE,
                    "cache_ttl_hours": settings.CACHE_TTL_HOURS
                },
                "health": {
                    "healthy": is_running and worker_running and beat_running,
                    "worker_running": worker_running,
                    "beat_running": beat_running,
                    "message": "すべて サービス normally 動作中" if (is_running and worker_running and beat_running) else "一部 サービス 動作していません"
                }
            },
            "checked_at": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"同期状態 取得 failed: {e}")
        return {
            "status": "error",
            "message": f"同期状態 取得 きません: {str(e)}",
            "checked_at": datetime.now().isoformat()
        }


@router.post("/trigger-immediate")
async def trigger_immediate_analytics_sync() -> Dict[str, Any]:
    """手動 よる即座同期 トリガー"""
    try:
        from app.services.utils.service_manager import unified_service_manager
        from app.tasks.analytics_sync_tasks import sync_user_insights_task, sync_market_trends_task, sync_all_users_assets_task
        
        if not settings.ENABLE_ANALYTICS_SYNC:
            raise HTTPException(
                status_code=400,
                detail="analysis同期サービス 無効化されています"
            )
        
        # まずサービス execute中 あるこ  確認
        service_status = await unified_service_manager.get_service_status('analytics_sync')
        if service_status.get('status') != 'running':
            # サービス起動 試行
            start_result = await unified_service_manager.start_service('analytics_sync')
            if start_result.get('status') != 'success':
                raise HTTPException(
                    status_code=500,
                    detail=f"同期サービス 起動 きません: {start_result.get('message')}"
                )
        
        # 各種同期タスク トリガー
        try:
            insight_task = sync_user_insights_task.delay()
            trends_task = sync_market_trends_task.delay()
            assets_task = sync_all_users_assets_task.delay()
            
            return {
                "status": "triggered",
                "message": "同期タスク normally 送信されました",
                "task_ids": {
                    "insights": insight_task.id,
                    "trends": trends_task.id,
                    "assets": assets_task.id
                },
                "triggered_at": datetime.now().isoformat()
            }
        except Exception as task_error:
            logger.error(f"同期タスク 送信 failed: {task_error}")
            raise HTTPException(
                status_code=500,
                detail=f"同期タスク 送信 failed: {str(task_error)}"
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"即座同期 トリガー failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"同期トリガー failed: {str(e)}"
        )


@router.get("/health")
async def sync_services_health() -> Dict[str, Any]:
    """同期サービス ヘルス状態 チェック"""
    try:
        from app.services.utils.service_manager import unified_service_manager
        
        if not settings.ENABLE_ANALYTICS_SYNC:
            return {
                "status": "success",
                "health_check": {
                    "healthy": False,
                    "message": "同期サービス 無効化されています"
                },
                "checked_at": datetime.now().isoformat()
            }
        
        service_status = await unified_service_manager.get_service_status('analytics_sync')
        is_running = service_status.get('status') == 'running'
        worker_running = service_status.get('worker_running', False)
        beat_running = service_status.get('beat_running', False)
        
        healthy = is_running and worker_running and beat_running
        
        return {
            "status": "success",
            "health_check": {
                "healthy": healthy,
                "message": "Sync services are running." if healthy else "Some sync services are not running."
            },
            "checked_at": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"ヘルスチェック failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/start")
async def start_analytics_sync_service() -> Dict[str, Any]:
    """analysis同期サービス 起動"""
    try:
        from app.services.utils.service_manager import unified_service_manager
        
        if not settings.ENABLE_ANALYTICS_SYNC:
            raise HTTPException(
                status_code=400,
                detail="analysissyncservice在configure中disabled"
            )
        
        # サービス 起動
        result = await unified_service_manager.start_service('analytics_sync')
        
        if result.get('status') == 'success':
            return {
                "status": "success",
                "message": "analysis同期サービス 起動 successしました",
                "details": result
            }
        elif result.get('status') == 'already_running':
            return {
                "status": "already_running",
                "message": "analysis同期サービス 既 execute中 す",
                "details": result
            }
        else:
            raise HTTPException(
                status_code=500,
                detail=f"同期サービス 起動 failed: {result.get('message')}"
            )

    except Exception as e:
        logger.error(f"同期サービス 起動 failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"同期サービス 起動 failed: {str(e)}"
        )

@router.post("/stop", 
    summary="analysis同期サービス stop",
    description="Celeryベース analysis結果同期サービス（Worker Beat） stopします。",
    response_model=Dict[str, Any],
    status_code=200)
async def stop_analytics_sync_service() -> Dict[str, Any]:
    """stopanalysissyncservice"""
    try:
        from app.services.utils.service_manager import unified_service_manager
        
        if not settings.ENABLE_ANALYTICS_SYNC:
            raise HTTPException(
                status_code=400,
                detail="analysissyncservice在configure中disabled"
            )
        
        # stopservice
        result = await unified_service_manager.stop_service('analytics_sync')
        
        if result.get('status') == 'success':
            return {
                "status": "success",
                "message": "analysis同期サービス stop successしました",
                "details": result
            }
        else:
            raise HTTPException(
                status_code=500,
                detail=f"analysis同期サービス stop failed: {result.get('message')}"
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"analysis同期サービス stop failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"analysis同期サービス stop failed: {str(e)}"
        )

@router.get("/cache-stats")
async def get_cache_statistics() -> Dict[str, Any]:
    """キャッシュ統計情報 取得"""
    try:
        # ここ Firestoreキャッシュ統計 取得するロジック 実装 きます
        # 例：キャッシュヒット率、キャッシュサイズ、期限切れdataなど
        
        return {
            "status": "success",
            "cache_stats": {
                "user_insights_cached": "統計中...",
                "market_trends_cached": "統計中...",
                "aggregated_data_cached": "統計中...",
                "cache_hit_rate": "95%",
                "avg_response_time_ms": 15.2
            },
            "message": "キャッシュ統計機能 開発中",
            "retrieved_at": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"キャッシュ統計 取得 failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ================ 補助関数 ================

# note：現在、同期タスク sync_starter よって統一管理されており、ここ Celeryタスク directly呼び出す必要 not available
