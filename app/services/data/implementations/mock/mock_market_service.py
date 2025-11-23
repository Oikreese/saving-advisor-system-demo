"""
模擬市場dataサービス 実装

既存 BigQueryanalysisエンジン 基づく実装
"""

from typing import Dict, List, Any, Optional
import logging

from app.services.data.interfaces.market_data_interface import MarketDataInterface
from app.services.bigquery.analytics_engine import BigQueryAnalyticsEngine
from app.services.bigquery.enhanced_client import EnhancedBigQueryClient


logger = logging.getLogger(__name__)


class MockMarketDataService(MarketDataInterface):
    """
    模擬市場dataサービス
    
    現在 実装：既存 BigQueryanalysisエンジン use
    将来 移行：Mercariメインアプリケーション 市場dataAPI呼び出し 置き換え
    """
    
    def __init__(self, 
                 analytics_engine: Optional[BigQueryAnalyticsEngine] = None,
                 bigquery_client: Optional[EnhancedBigQueryClient] = None):
        self.analytics_engine = analytics_engine or BigQueryAnalyticsEngine()
        self.bigquery_client = bigquery_client or EnhancedBigQueryClient()
        logger.info("MockMarketDataService initialized - using BigQuery analytics backend")
    
    async def get_market_trends(self, asset_type: Optional[str] = None) -> Dict[str, Any]:
        """市場トレンドdata 取得"""
        try:
            if asset_type:
                # 特定 assetタイプ トレンド 取得
                trends = await self.analytics_engine.analyze_asset_allocation_trends()
                # 結果 from 特定 assetタイプ data フィルタリング
                filtered_trends = self._filter_trends_by_asset_type(trends, asset_type)
                return filtered_trends
            else:
                # すべて assetタイプ 全体 なトレンド 取得
                return await self.analytics_engine.analyze_market_trends()
        except Exception as e:
            logger.error(f"Error getting market trends for asset_type {asset_type}: {e}")
            return {}
    
    async def get_asset_performance(self, asset_type: str, period_days: int = 30) -> Dict[str, Any]:
        """assetパフォーマンスdata 取得"""
        try:
            # BigQueryanalysisエンジン useしてassetパフォーマンス 取得
            performance_data = await self.analytics_engine.analyze_asset_performance_trends(
                asset_type=asset_type,
                days=period_days
            )
            return performance_data
        except Exception as e:
            logger.error(f"Error getting asset performance for {asset_type}: {e}")
            return {}
    
    async def get_market_insights(self) -> Dict[str, Any]:
        """市場インサイトanalysis 取得"""
        try:
            # 総合 な市場インサイト 取得
            insights = await self.analytics_engine.get_predictive_insights()
            return insights
        except Exception as e:
            logger.error(f"Error getting market insights: {e}")
            return {}
    
    async def get_popular_categories(self, limit: int = 10) -> List[Dict[str, Any]]:
        """人気商品カテゴリ 取得"""
        try:
            # BigQuery from 人気カテゴリdata 取得
            categories_data = await self.bigquery_client.get_popular_categories(limit=limit)
            return categories_data or []
        except Exception as e:
            logger.error(f"Error getting popular categories: {e}")
            return []
    
    async def get_price_analytics(self, 
                                category: Optional[str] = None,
                                time_range: Optional[str] = '30d') -> Dict[str, Any]:
        """価格analysisdata 取得"""
        try:
            # 時間範囲 日数 変換
            days_map = {'7d': 7, '30d': 30, '90d': 90, '1y': 365}
            days = days_map.get(time_range, 30)
            
            price_analytics = await self.bigquery_client.get_price_analytics(
                category=category,
                days=days
            )
            return price_analytics or {}
        except Exception as e:
            logger.error(f"Error getting price analytics for category {category}: {e}")
            return {}
    
    async def get_user_segment_insights(self, segment: str) -> Dict[str, Any]:
        """userセグメント インサイト 取得"""
        try:
            # analysisエンジン useしてuserセグメントdata 取得
            segment_insights = await self.analytics_engine.analyze_user_segmentation()
            
            # 結果 from 特定 セグメント data 抽出
            if segment in segment_insights.get('segments', {}):
                return {
                    'segment': segment,
                    'insights': segment_insights['segments'][segment],
                    'market_behavior': segment_insights.get('market_behavior', {}),
                    'recommendations': segment_insights.get('recommendations', [])
                }
            return {}
        except Exception as e:
            logger.error(f"Error getting user segment insights for {segment}: {e}")
            return {}
    
    async def get_economic_indicators(self) -> Dict[str, Any]:
        """経済指標data 取得"""
        try:
            # BigQuery from 経済指標関連 data 取得
            indicators = await self.bigquery_client.get_economic_indicators()
            return indicators or {}
        except Exception as e:
            logger.error(f"Error getting economic indicators: {e}")
            return {}
    
    async def get_competition_analysis(self, asset_type: str) -> Dict[str, Any]:
        """競合analysisdata 取得"""
        try:
            # 特定 assetタイプ 競合環境analysis 取得
            competition_data = await self.analytics_engine.analyze_competition_landscape(asset_type)
            return competition_data
        except Exception as e:
            logger.error(f"Error getting competition analysis for {asset_type}: {e}")
            return {}
    
    def _filter_trends_by_asset_type(self, trends_data: Dict[str, Any], asset_type: str) -> Dict[str, Any]:
        """assetタイプ based onトレンドdata フィルタリング"""
        try:
            if not trends_data or 'asset_trends' not in trends_data:
                return {}
                
            asset_trends = trends_data['asset_trends']
            if asset_type in asset_trends:
                return {
                    'asset_type': asset_type,
                    'trends': asset_trends[asset_type],
                    'timestamp': trends_data.get('timestamp'),
                    'summary': trends_data.get('summary', {}).get(asset_type)
                }
            return {}
        except Exception as e:
            logger.error(f"Error filtering trends by asset type {asset_type}: {e}")
            return {}


# シングルトンファクトリ関数
_mock_market_service_instance = None

def get_mock_market_service() -> MockMarketDataService:
    """MockMarketDataService シングルトンインスタンス 取得"""
    global _mock_market_service_instance
    if _mock_market_service_instance is None:
        _mock_market_service_instance = MockMarketDataService()
    return _mock_market_service_instance
