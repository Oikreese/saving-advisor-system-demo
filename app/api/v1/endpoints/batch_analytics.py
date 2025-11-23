"""
批处理分析结果 API

提供查询批处理任务结果的API端点
替代 BigQuery Analytics API
"""
from fastapi import APIRouter, HTTPException, Query
from typing import Dict, Any, List, Optional
from datetime import datetime
import redis
import json

from app.core.config import settings
from app.core.logging import logger

router = APIRouter()

# Redis客户端
def get_redis_client():
    """获取Redis客户端"""
    return redis.from_url(settings.REDIS_URL, decode_responses=True)


@router.get("/user-behavior", response_model=Dict[str, Any])
async def get_user_behavior_analysis(
    date: Optional[str] = Query(None, description="指定日期 (YYYYMMDD)，默认获取最新")
) -> Dict[str, Any]:
    """
    获取用户行为分析结果
    
    每日凌晨2点自动执行，结果缓存24小时
    """
    try:
        r = get_redis_client()
        
        if date:
            cache_key = f"batch_analysis:user_behavior_analysis:{date}"
        else:
            cache_key = "batch_analysis:user_behavior_analysis:latest"
        
        result = r.get(cache_key)
        
        if not result:
            raise HTTPException(
                status_code=404,
                detail=f"未找到分析结果。最新分析时间：{date or '未知'}"
            )
        
        data = json.loads(result)
        
        return {
            "success": True,
            "data": data,
            "cache_key": cache_key,
            "retrieved_at": datetime.now().isoformat()
        }
        
    except json.JSONDecodeError as e:
        logger.error(f"JSON解析失败: {e}")
        raise HTTPException(status_code=500, detail="数据格式错误")
    except Exception as e:
        logger.error(f"获取用户行为分析失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/recommendations", response_model=Dict[str, Any])
async def get_recommendation_performance(
    hour: Optional[str] = Query(None, description="指定小时 (YYYYMMDDHH)，默认获取最新")
) -> Dict[str, Any]:
    """
    获取推荐效果分析结果
    
    每4小时自动执行，结果缓存6小时
    """
    try:
        r = get_redis_client()
        
        if hour:
            cache_key = f"batch_analysis:recommendation_performance:{hour}"
        else:
            cache_key = "batch_analysis:recommendation_performance:latest"
        
        result = r.get(cache_key)
        
        if not result:
            raise HTTPException(
                status_code=404,
                detail=f"未找到分析结果。最新分析时间：{hour or '未知'}"
            )
        
        data = json.loads(result)
        
        return {
            "success": True,
            "data": data,
            "cache_key": cache_key,
            "retrieved_at": datetime.now().isoformat()
        }
        
    except json.JSONDecodeError as e:
        logger.error(f"JSON解析失败: {e}")
        raise HTTPException(status_code=500, detail="数据格式错误")
    except Exception as e:
        logger.error(f"获取推荐效果分析失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/market-trends", response_model=Dict[str, Any])
async def get_market_trends_analysis(
    date: Optional[str] = Query(None, description="指定日期 (YYYYMMDD)，默认获取最新")
) -> Dict[str, Any]:
    """
    获取市场趋势分析结果
    
    每天凌晨3点自动执行，结果缓存24小时
    """
    try:
        r = get_redis_client()
        
        if date:
            cache_key = f"batch_analysis:market_trends:{date}"
        else:
            cache_key = "batch_analysis:market_trends:latest"
        
        result = r.get(cache_key)
        
        if not result:
            raise HTTPException(
                status_code=404,
                detail=f"未找到分析结果。最新分析时间：{date or '未知'}"
            )
        
        data = json.loads(result)
        
        return {
            "success": True,
            "data": data,
            "cache_key": cache_key,
            "retrieved_at": datetime.now().isoformat()
        }
        
    except json.JSONDecodeError as e:
        logger.error(f"JSON解析失败: {e}")
        raise HTTPException(status_code=500, detail="数据格式错误")
    except Exception as e:
        logger.error(f"获取市场趋势分析失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/all", response_model=Dict[str, Any])
async def get_all_analyses() -> Dict[str, Any]:
    """
    获取所有最新的批处理分析结果
    """
    try:
        r = get_redis_client()
        
        analyses = {}
        analysis_types = [
            "user_behavior_analysis",
            "recommendation_performance",
            "market_trends"
        ]
        
        for analysis_type in analysis_types:
            cache_key = f"batch_analysis:{analysis_type}:latest"
            result = r.get(cache_key)
            
            if result:
                try:
                    analyses[analysis_type] = json.loads(result)
                except json.JSONDecodeError:
                    logger.warning(f"无法解析 {analysis_type} 的数据")
                    analyses[analysis_type] = None
            else:
                analyses[analysis_type] = None
        
        available_count = sum(1 for v in analyses.values() if v is not None)
        
        return {
            "success": True,
            "available_analyses": available_count,
            "total_analyses": len(analysis_types),
            "data": analyses,
            "retrieved_at": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"获取所有分析失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/history/{analysis_type}", response_model=Dict[str, Any])
async def get_analysis_history(
    analysis_type: str,
    limit: int = Query(10, ge=1, le=100, description="返回结果数量")
) -> Dict[str, Any]:
    """
    获取指定分析类型的历史记录
    
    analysis_type: user_behavior_analysis, recommendation_performance, market_trends
    """
    try:
        r = get_redis_client()
        
        # 搜索历史记录键
        pattern = f"batch_analysis:{analysis_type}:*"
        keys = r.keys(pattern)
        
        # 排除 'latest' 键
        keys = [k for k in keys if not k.endswith(':latest')]
        
        # 按日期排序（假设键包含日期）
        keys.sort(reverse=True)
        keys = keys[:limit]
        
        history = []
        for key in keys:
            result = r.get(key)
            if result:
                try:
                    data = json.loads(result)
                    history.append({
                        "key": key,
                        "analyzed_at": data.get("analyzed_at"),
                        "summary": {
                            "analysis_type": data.get("analysis_type"),
                            "execution_time": data.get("execution_time_seconds"),
                        }
                    })
                except json.JSONDecodeError:
                    continue
        
        return {
            "success": True,
            "analysis_type": analysis_type,
            "count": len(history),
            "history": history,
            "retrieved_at": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"获取历史记录失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status", response_model=Dict[str, Any])
async def get_batch_system_status() -> Dict[str, Any]:
    """
    获取批处理系统状态
    """
    try:
        r = get_redis_client()
        
        # 检查各个分析的最新结果
        analyses_status = {}
        analysis_types = {
            "user_behavior_analysis": "用户行为分析",
            "recommendation_performance": "推荐效果分析",
            "market_trends": "市场趋势分析"
        }
        
        for key, name in analysis_types.items():
            cache_key = f"batch_analysis:{key}:latest"
            result = r.get(cache_key)
            
            if result:
                try:
                    data = json.loads(result)
                    analyses_status[key] = {
                        "name": name,
                        "status": "available",
                        "last_run": data.get("analyzed_at"),
                        "execution_time": data.get("execution_time_seconds")
                    }
                except json.JSONDecodeError:
                    analyses_status[key] = {
                        "name": name,
                        "status": "error",
                        "error": "数据格式错误"
                    }
            else:
                analyses_status[key] = {
                    "name": name,
                    "status": "no_data",
                    "message": "尚无分析结果"
                }
        
        # Redis连接状态
        try:
            r.ping()
            redis_status = "connected"
        except:
            redis_status = "disconnected"
        
        return {
            "success": True,
            "system_status": {
                "redis": redis_status,
                "analyses": analyses_status
            },
            "info": {
                "description": "批处理分析系统（替代BigQuery）",
                "scheduler": "Celery Beat",
                "cache": "Redis",
                "docs": "/api/v1/batch-analytics/docs"
            },
            "checked_at": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"获取系统状态失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/trigger/{analysis_type}", response_model=Dict[str, Any])
async def trigger_analysis(
    analysis_type: str
) -> Dict[str, Any]:
    """
    手动触发批处理分析任务
    
    analysis_type: user_behavior, recommendations, market_trends
    """
    try:
        from app.tasks.batch_tasks import (
            trigger_user_behavior_analysis,
            trigger_recommendation_analysis,
            trigger_market_trends_analysis
        )
        
        task_map = {
            "user_behavior": trigger_user_behavior_analysis,
            "recommendations": trigger_recommendation_analysis,
            "market_trends": trigger_market_trends_analysis
        }
        
        if analysis_type not in task_map:
            raise HTTPException(
                status_code=400,
                detail=f"不支持的分析类型: {analysis_type}"
            )
        
        # 触发任务
        task = task_map[analysis_type]()
        
        return {
            "success": True,
            "message": f"{analysis_type} 分析任务已触发",
            "task_id": task.id,
            "status": "pending",
            "triggered_at": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"触发任务失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

