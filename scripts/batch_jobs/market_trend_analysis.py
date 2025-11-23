#!/usr/bin/env python3
"""
Market trends analysis batch processing task

Replaces BigQuery market trends analysis
Executes daily
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


async def analyze_market_trends(days: int = 30) -> Dict[str, Any]:
    """
    Analyze market trends
    
    Args:
        days: Number of days to analyze
        
    Returns:
        Analysis results dictionary
    """
    start_time = datetime.now()
    logger.info(f"📈 Starting market trends analysis for the past {days} days...")
    
    try:
        async with get_db_session() as session:
            repo = AnalyticsRepository(session)
            
            # 1. Asset type trends
            logger.info("  💎 Analyzing asset type trends...")
            asset_trends = await repo.get_asset_type_trends(days)
            
            # 2. Transaction volume trends
            logger.info("  📊 Analyzing transaction volume trends...")
            transaction_trends = await repo.get_transaction_volume_trends(days)
            
            # 3. Price trends
            logger.info("  💰 Analyzing price trends...")
            price_trends = await repo.get_price_trends(days)
            
            # Assemble results
            results = {
                'analysis_type': 'market_trends',
                'period_days': days,
                'asset_trends': asset_trends,
                'transaction_trends': transaction_trends,
                'price_trends': price_trends,
                'analyzed_at': datetime.now().isoformat(),
                'execution_time_seconds': (datetime.now() - start_time).total_seconds()
            }
            
            # Save to Redis
            await save_analysis_results('market_trends', results)
            
            duration = (datetime.now() - start_time).total_seconds()
            logger.info(f"✅ Market trends analysis completed! Took {duration:.2f} seconds")
            
            return results
            
    except Exception as e:
        logger.error(f"❌ Market trends analysis failed: {e}", exc_info=True)
        raise


async def save_analysis_results(key: str, data: Dict[str, Any]):
    """Save analysis results to Redis"""
    try:
        import redis
        from app.core.config import settings
        
        redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)
        
        # Save results, TTL = 24 hours
        cache_key = f"batch_analysis:{key}:{datetime.now().strftime('%Y%m%d')}"
        redis_client.setex(
            cache_key,
            86400,  # 24 hours
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
    print("  📈 Market Trends Analysis Task")
    print("=" * 60)
    
    results = await analyze_market_trends(days=30)
    
    print("\n" + "=" * 60)
    print("  Analysis Summary:")
    print("=" * 60)
    print(f"  Asset types: {len(results.get('asset_trends', []))}")
    print(f"  Execution time: {results.get('execution_time_seconds', 0):.2f} seconds")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
