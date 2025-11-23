#!/usr/bin/env python3
"""
Recommendation performance analysis batch processing task

Replaces BigQuery recommendation performance analysis
Executes every 4 hours
"""
import asyncio
import sys
import os
from datetime import datetime, timedelta
from typing import Dict, Any
import json

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from app.db.database import get_db_session
from app.db.repositories.analytics_repository import AnalyticsRepository
from app.core.logging import logger


async def analyze_recommendation_performance(hours: int = 24) -> Dict[str, Any]:
    """
    Analyze recommendation system performance
    
    Args:
        hours: Number of hours to analyze
        
    Returns:
        Analysis results dictionary
    """
    start_time = datetime.now()
    logger.info(f"🎯 Starting recommendation performance analysis for the past {hours} hours...")
    
    try:
        async with get_db_session() as session:
            repo = AnalyticsRepository(session)
            
            # 1. Recommendation acceptance rate
            logger.info("  📊 Analyzing recommendation acceptance rate...")
            acceptance_rate = await repo.get_recommendation_acceptance_rate(hours)
            
            # 2. AI session statistics
            logger.info("  🤖 Analyzing AI session statistics...")
            session_stats = await repo.get_ai_session_statistics(hours)
            
            # 3. Recommendation quality metrics
            logger.info("  ⭐ Analyzing recommendation quality...")
            quality_metrics = await repo.get_recommendation_quality_metrics(hours)
            
            # Assemble results
            results = {
                'analysis_type': 'recommendation_performance',
                'period_hours': hours,
                'acceptance_rate': acceptance_rate,
                'session_stats': session_stats,
                'quality_metrics': quality_metrics,
                'analyzed_at': datetime.now().isoformat(),
                'execution_time_seconds': (datetime.now() - start_time).total_seconds()
            }
            
            # Save to Redis
            await save_analysis_results('recommendation_performance', results)
            
            duration = (datetime.now() - start_time).total_seconds()
            logger.info(f"✅ Recommendation performance analysis completed! Took {duration:.2f} seconds")
            
            return results
            
    except Exception as e:
        logger.error(f"❌ Recommendation performance analysis failed: {e}", exc_info=True)
        raise


async def save_analysis_results(key: str, data: Dict[str, Any]):
    """Save analysis results to Redis"""
    try:
        import redis
        from app.core.config import settings
        
        redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)
        
        # Save results, TTL = 6 hours
        cache_key = f"batch_analysis:{key}:{datetime.now().strftime('%Y%m%d%H')}"
        redis_client.setex(
            cache_key,
            21600,  # 6 hours
            json.dumps(data, default=str)
        )
        
        # Update latest result
        latest_key = f"batch_analysis:{key}:latest"
        redis_client.set(latest_key, json.dumps(data, default=str))
        
        logger.info(f"  💾 Analysis results cached: {cache_key}")
        
    except Exception as e:
        logger.warning(f"  ⚠️  Cache save failed: {e}")


async def main():
    """Main function - for standalone execution"""
    print("=" * 60)
    print("  🎯 Recommendation Performance Analysis Task")
    print("=" * 60)
    
    results = await analyze_recommendation_performance(hours=24)
    
    print("\n" + "=" * 60)
    print("  Analysis Summary:")
    print("=" * 60)
    print(f"  Acceptance rate: {results.get('acceptance_rate', {}).get('rate', 0):.2%}")
    print(f"  AI sessions: {results.get('session_stats', {}).get('total_sessions', 0)}")
    print(f"  Execution time: {results.get('execution_time_seconds', 0):.2f} seconds")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
