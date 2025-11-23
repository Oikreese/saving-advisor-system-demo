"""
批处理任务 - Celery 定时任务配置

替代 BigQuery 批处理系统
使用 Celery Beat 进行任务调度
"""
import asyncio
from celery import Celery
from celery.schedules import crontab
from datetime import datetime
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from app.core.config import settings
from app.core.logging import logger

# 创建 Celery 应用
celery_app = Celery(
    'batch_tasks',
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL
)

# Celery 配置
celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='Asia/Tokyo',
    enable_utc=True,
    task_track_started=True,
    task_time_limit=3600,  # 1小时超时
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=50,
)


@celery_app.on_after_configure.connect
def setup_periodic_tasks(sender, **kwargs):
    """配置定时任务"""
    
    # 每天凌晨2点：用户行为分析
    sender.add_periodic_task(
        crontab(hour=2, minute=0),
        analyze_user_behavior_task.s(),
        name='用户行为分析 (每日凌晨2点)'
    )
    
    # 每4小时：推荐效果分析
    sender.add_periodic_task(
        crontab(minute=0, hour='*/4'),
        analyze_recommendation_performance_task.s(),
        name='推荐效果分析 (每4小时)'
    )
    
    # 每天凌晨3点：市场趋势分析
    sender.add_periodic_task(
        crontab(hour=3, minute=0),
        analyze_market_trends_task.s(),
        name='市场趋势分析 (每日凌晨3点)'
    )
    
    # 每周一凌晨4点：用户细分分析
    sender.add_periodic_task(
        crontab(hour=4, minute=0, day_of_week=1),
        user_segmentation_task.s(),
        name='用户细分分析 (每周一凌晨4点)'
    )
    
    logger.info("✅ Celery 定时任务已配置")


@celery_app.task(name='batch.analyze_user_behavior', bind=True)
def analyze_user_behavior_task(self):
    """用户行为分析任务"""
    task_id = self.request.id
    logger.info(f"🚀 [Task {task_id}] 开始用户行为分析...")
    
    try:
        from scripts.batch_jobs.user_behavior_analysis import analyze_user_behavior
        result = asyncio.run(analyze_user_behavior(days=7))
        
        logger.info(f"✅ [Task {task_id}] 用户行为分析完成")
        return {
            'status': 'success',
            'task_id': task_id,
            'result': result
        }
        
    except Exception as e:
        logger.error(f"❌ [Task {task_id}] 用户行为分析失败: {e}")
        raise


@celery_app.task(name='batch.analyze_recommendation_performance', bind=True)
def analyze_recommendation_performance_task(self):
    """推荐效果分析任务"""
    task_id = self.request.id
    logger.info(f"🚀 [Task {task_id}] 开始推荐效果分析...")
    
    try:
        from scripts.batch_jobs.recommendation_analysis import analyze_recommendation_performance
        result = asyncio.run(analyze_recommendation_performance(hours=24))
        
        logger.info(f"✅ [Task {task_id}] 推荐效果分析完成")
        return {
            'status': 'success',
            'task_id': task_id,
            'result': result
        }
        
    except Exception as e:
        logger.error(f"❌ [Task {task_id}] 推荐效果分析失败: {e}")
        raise


@celery_app.task(name='batch.analyze_market_trends', bind=True)
def analyze_market_trends_task(self):
    """市场趋势分析任务"""
    task_id = self.request.id
    logger.info(f"🚀 [Task {task_id}] 开始市场趋势分析...")
    
    try:
        from scripts.batch_jobs.market_trend_analysis import analyze_market_trends
        result = asyncio.run(analyze_market_trends(days=30))
        
        logger.info(f"✅ [Task {task_id}] 市场趋势分析完成")
        return {
            'status': 'success',
            'task_id': task_id,
            'result': result
        }
        
    except Exception as e:
        logger.error(f"❌ [Task {task_id}] 市场趋势分析失败: {e}")
        raise


@celery_app.task(name='batch.user_segmentation', bind=True)
def user_segmentation_task(self):
    """用户细分分析任务"""
    task_id = self.request.id
    logger.info(f"🚀 [Task {task_id}] 开始用户细分分析...")
    
    try:
        # TODO: 实现用户细分分析逻辑
        logger.info(f"✅ [Task {task_id}] 用户细分分析完成")
        return {
            'status': 'success',
            'task_id': task_id,
            'message': '用户细分分析功能待实现'
        }
        
    except Exception as e:
        logger.error(f"❌ [Task {task_id}] 用户细分分析失败: {e}")
        raise


# 手动触发任务的辅助函数
def trigger_user_behavior_analysis():
    """手动触发用户行为分析"""
    return analyze_user_behavior_task.delay()


def trigger_recommendation_analysis():
    """手动触发推荐效果分析"""
    return analyze_recommendation_performance_task.delay()


def trigger_market_trends_analysis():
    """手动触发市场趋势分析"""
    return analyze_market_trends_task.delay()


if __name__ == '__main__':
    # 用于测试：启动 Celery worker
    celery_app.start()

