#!/usr/bin/env python3
"""
User behavior analysis batch processing task

Replaces BigQuery user behavior analysis
Executes daily at 2:00 AM
"""
import asyncio
import sys
import os
from datetime import datetime, timedelta
from typing import Dict, Any
import json

# Add project root directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from app.db.database import get_db_session
from app.db.repositories.analytics_repository import AnalyticsRepository
from app.core.logging import logger


async def analyze_user_behavior(days: int = 7) -> Dict[str, Any]:
    """
    Analyze user behavior (past N days)
    
    Args:
        days: Number of days to analyze
        
    Returns:
        Analysis results dictionary
    """
    start_time = datetime.now()
    logger.info(f"🔍 Starting user behavior analysis for the past {days} days...")
    
    try:
        async with get_db_session() as session:
            repo = AnalyticsRepository(session)
            
            # 1. Active user statistics
            logger.info("  📊 Analyzing active users...")
            active_users = await repo.get_active_users_stats(days)
            
            # 2. Transaction behavior analysis
            logger.info("  💳 Analyzing transaction behavior...")
            transaction_stats = await repo.get_transaction_statistics(days)
            
            # 3. Asset change analysis
            logger.info("  💰 Analyzing asset changes...")
            asset_changes = await repo.get_asset_change_statistics(days)
            
            # 4. User engagement analysis
            logger.info("  📈 Analyzing user engagement...")
            engagement_stats = await repo.get_user_engagement_stats(days)
            
            # Assemble results
            results = {
                'analysis_type': 'user_behavior',
                'period_days': days,
                'active_users': active_users,
                'transactions': transaction_stats,
                'asset_changes': asset_changes,
                'engagement': engagement_stats,
                'analyzed_at': datetime.now().isoformat(),
                'execution_time_seconds': (datetime.now() - start_time).total_seconds()
            }
            
            # 5. Save analysis results to cache (Redis)
            await save_analysis_results('user_behavior_analysis', results)
            
            duration = (datetime.now() - start_time).total_seconds()
            logger.info(f"✅ User behavior analysis completed! Took {duration:.2f} seconds")
            
            return results
            
    except Exception as e:
        logger.error(f"❌ User behavior analysis failed: {e}", exc_info=True)
        raise


async def save_analysis_results(key: str, data: Dict[str, Any]):
    """Save analysis results to Redis"""
    try:
        import redis
        from app.core.config import settings
        
        # Connect to Redis
        redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)
        
        # Save results, TTL = 24 hours
        cache_key = f"batch_analysis:{key}:{datetime.now().strftime('%Y%m%d')}"
        redis_client.setex(
            cache_key,
            86400,  # 24 hours
            json.dumps(data, default=str)
        )
        
        # Also update the latest result key (no expiration)
        latest_key = f"batch_analysis:{key}:latest"
        redis_client.set(latest_key, json.dumps(data, default=str))
        
        logger.info(f"  💾 Analysis results cached: {cache_key}")
        
    except Exception as e:
        logger.warning(f"  ⚠️  Cache save failed: {e}")


async def main():
    """Main function - for standalone execution"""
    print("=" * 60)
    print("  📊 User Behavior Analysis Task")
    print("=" * 60)
    
    # Initialize database
    from app.db.database import init_db
    await init_db()
    logger.info("✅ Database initialization completed")
    
    results = await analyze_user_behavior(days=7)
    
    print("\n" + "=" * 60)
    print("  Analysis Summary:")
    print("=" * 60)
    print(f"  Active users: {results.get('active_users', {}).get('count', 0)}")
    print(f"  Total transactions: {results.get('transactions', {}).get('total_count', 0)}")
    print(f"  Execution time: {results.get('execution_time_seconds', 0):.2f} seconds")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
