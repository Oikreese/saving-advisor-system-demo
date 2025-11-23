"""
userdataサービスインターフェース

user関連 dataアクセス 抽象化し、模擬dataソースまた MercariメインアプリケーションAPI from  data取得 サポート
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional
from datetime import datetime

from app.models.assets import UserPortfolio, UserAsset, TransactionBehavior, RiskProfile


class UserDataInterface(ABC):
    """
    userdataサービス 抽象インターフェース
    
    現段階  Firestore/BigQuery from 模擬data 取得
    将来   Mercariメインアプリケーション in部API呼び出し 切り替え可能
    """
    
    @abstractmethod
    async def get_user_portfolio(self, user_id: str) -> Optional[UserPortfolio]:
        """
        user assetportfolio 取得
        
        Args:
            user_id: userID
            
        Returns:
            user assetportfoliodata、user existsしない場合 None 返す
        """
        pass
    
    @abstractmethod
    async def get_user_assets(self, user_id: str) -> List[UserAsset]:
        """
        user すべて asset 取得
        
        Args:
            user_id: userID
            
        Returns:
            userasset list
        """
        pass
    
    @abstractmethod
    async def get_user_transaction_behavior(self, user_id: str) -> Optional[TransactionBehavior]:
        """
        user 取引行動data 取得
        
        Args:
            user_id: userID
            
        Returns:
            user 取引行動data
        """
        pass
    
    @abstractmethod
    async def get_user_risk_profile(self, user_id: str) -> Optional[RiskProfile]:
        """
        user リスク許容度 取得
        
        Args:
            user_id: userID
            
        Returns:
            user リスク許容度data
        """
        pass
    
    @abstractmethod
    async def get_user_basic_info(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        user 基本情報 取得
        
        Args:
            user_id: userID
            
        Returns:
            user 基本情報辞書
        """
        pass
    
    @abstractmethod
    async def update_user_assets(self, user_id: str, assets: List[UserAsset]) -> bool:
        """
        user asset情報 update
        
        Args:
            user_id: userID
            assets: newassetlist
            
        Returns:
            update successしたかどうか
        """
        pass
    
    @abstractmethod
    async def get_user_historical_data(self, 
                                     user_id: str, 
                                     start_date: datetime, 
                                     end_date: datetime) -> Dict[str, Any]:
        """
        user 履歴data 取得
        
        Args:
            user_id: userID
            start_date: 開始日
            end_date: 終了日
            
        Returns:
            user 履歴data
        """
        pass
    
    @abstractmethod
    async def check_user_exists(self, user_id: str) -> bool:
        """
        user existsするかどうか 確認
        
        Args:
            user_id: userID
            
        Returns:
            user existsするかどうか
        """
        pass
