"""
市場dataサービスインターフェース

市場関連 dataアクセス 抽象化し、模擬dataソースまた MercariメインアプリケーションAPI from  data取得 サポート
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional
from datetime import datetime


class MarketDataInterface(ABC):
    """
    市場dataサービス 抽象インターフェース
    
    現段階  BigQuery/外部API from 模擬data 取得
    将来   Mercariメインアプリケーション in部市場dataAPI呼び出し 切り替え可能
    """
    
    @abstractmethod
    async def get_market_trends(self, asset_type: Optional[str] = None) -> Dict[str, Any]:
        """
        市場トレンドdata 取得
        
        Args:
            asset_type: assetタイプ、None すべて タイプ 取得するこ  意味する
            
        Returns:
            市場トレンドdata
        """
        pass
    
    @abstractmethod
    async def get_asset_performance(self, asset_type: str, period_days: int = 30) -> Dict[str, Any]:
        """
        assetパフォーマンスdata 取得
        
        Args:
            asset_type: assetタイプ
            period_days: 統計期間（日数）
            
        Returns:
            assetパフォーマンスdata
        """
        pass
    
    @abstractmethod
    async def get_market_insights(self) -> Dict[str, Any]:
        """
        市場インサイトanalysis 取得
        
        Returns:
            トレンドanalysis 予測 including市場インサイトdata
        """
        pass
    
    @abstractmethod
    async def get_popular_categories(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        人気商品カテゴリ 取得
        
        Args:
            limit: 返すcount 制限
            
        Returns:
            人気カテゴリ list
        """
        pass
    
    @abstractmethod
    async def get_price_analytics(self, 
                                category: Optional[str] = None,
                                time_range: Optional[str] = '30d') -> Dict[str, Any]:
        """
        価格analysisdata 取得
        
        Args:
            category: 商品カテゴリ、None すべて カテゴリ 意味する
            time_range: 時間範囲 ('7d', '30d', '90d', '1y')
            
        Returns:
            価格analysisdata
        """
        pass
    
    @abstractmethod
    async def get_user_segment_insights(self, segment: str) -> Dict[str, Any]:
        """
        userセグメント インサイト 取得
        
        Args:
            segment: userセグメントタイプ
            
        Returns:
            そ セグメント userグループ 市場行動インサイト
        """
        pass
    
    @abstractmethod
    async def get_economic_indicators(self) -> Dict[str, Any]:
        """
        経済指標data 取得
        
        Returns:
            関連する経済指標data
        """
        pass
    
    @abstractmethod
    async def get_competition_analysis(self, asset_type: str) -> Dict[str, Any]:
        """
        競合analysisdata 取得
        
        Args:
            asset_type: assetタイプ
            
        Returns:
            競合環境analysisdata
        """
        pass
