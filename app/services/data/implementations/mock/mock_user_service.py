"""
模擬userdataサービス 実装

既存 Firestore/BigQuery実装 based on、将来 MercariメインアプリAPIへ 移行準備 行う
"""

from typing import Dict, List, Any, Optional
from datetime import datetime
import logging

from app.services.data.interfaces.user_data_interface import UserDataInterface
from app.models.assets import UserPortfolio, UserAsset, TransactionBehavior, RiskProfile
from app.services.firestore.firestore_primary_service import FirestorePrimaryService
from app.services.bigquery.enhanced_client import EnhancedBigQueryClient


logger = logging.getLogger(__name__)


class MockUserDataService(UserDataInterface):
    """
    模擬userdataサービス
    
    現在 実装：既存 FirestoreおよびBigQueryサービス use
    将来 移行：MercariメインアプリAPI 呼び出すMercariUserDataService 置き換え
    """
    
    def __init__(self, 
                 firestore_service: Optional[FirestorePrimaryService] = None,
                 bigquery_client: Optional[EnhancedBigQueryClient] = None):
        self.firestore_service = firestore_service or FirestorePrimaryService()
        self.bigquery_client = bigquery_client or EnhancedBigQueryClient()
        logger.info("MockUserDataService initialized - using Firestore/BigQuery backend")
    
    async def get_user_portfolio(self, user_id: str) -> Optional[UserPortfolio]:
        """user assetportfolio 取得 - Firestore from 取得"""
        try:
            portfolio_data = await self.firestore_service.get_user_current_assets(user_id)
            if not portfolio_data:
                logger.warning(f"No portfolio found for user {user_id}")
                return None
                
            return UserPortfolio(**portfolio_data)
        except Exception as e:
            logger.error(f"Error getting user portfolio for {user_id}: {e}")
            return None
    
    async def get_user_assets(self, user_id: str) -> List[UserAsset]:
        """user assetlist 取得"""
        try:
            portfolio = await self.get_user_portfolio(user_id)
            if portfolio and portfolio.assets:
                return portfolio.assets
            return []
        except Exception as e:
            logger.error(f"Error getting user assets for {user_id}: {e}")
            return []
    
    async def get_user_transaction_behavior(self, user_id: str) -> Optional[TransactionBehavior]:
        """user 取引行動 取得 - BigQuery analysis"""
        try:
            # BigQueryクライアント useして取引行動analysis 取得
            behavior_data = await self.bigquery_client.get_user_behavior_analysis(user_id)
            if behavior_data:
                return TransactionBehavior(**behavior_data)
            return None
        except Exception as e:
            logger.error(f"Error getting transaction behavior for {user_id}: {e}")
            return None
    
    async def get_user_risk_profile(self, user_id: str) -> Optional[RiskProfile]:
        """user リスクプロファイル 取得"""
        try:
            # Firestore from user リスクプロファイル設定 取得
            risk_data = await self.firestore_service.get_user_risk_profile(user_id)
            if risk_data:
                return RiskProfile(**risk_data)
            return None
        except Exception as e:
            logger.error(f"Error getting risk profile for {user_id}: {e}")
            return None
    
    async def get_user_basic_info(self, user_id: str) -> Optional[Dict[str, Any]]:
        """user 基本情報 取得"""
        try:
            # Firestore from 基本user情報 取得
            user_info = await self.firestore_service.get_user_profile(user_id)
            return user_info
        except Exception as e:
            logger.error(f"Error getting user basic info for {user_id}: {e}")
            return None
    
    async def update_user_assets(self, user_id: str, assets: List[UserAsset]) -> bool:
        """user asset update"""
        try:
            # Firestore saveするfor assetlist 辞書形式 変換
            assets_data = [asset.dict() for asset in assets]
            success = await self.firestore_service.update_user_assets(user_id, assets_data)
            if success:
                logger.info(f"Successfully updated assets for user {user_id}")
            return success
        except Exception as e:
            logger.error(f"Error updating user assets for {user_id}: {e}")
            return False
    
    async def get_user_historical_data(self, 
                                     user_id: str, 
                                     start_date: datetime, 
                                     end_date: datetime) -> Dict[str, Any]:
        """user 履歴data 取得"""
        try:
            # BigQuery from 履歴取引 asset変動data 取得
            historical_data = await self.bigquery_client.get_user_historical_analytics(
                user_id, start_date, end_date
            )
            return historical_data or {}
        except Exception as e:
            logger.error(f"Error getting historical data for {user_id}: {e}")
            return {}
    
    async def check_user_exists(self, user_id: str) -> bool:
        """user existsするかどうか 確認"""
        try:
            user_info = await self.get_user_basic_info(user_id)
            return user_info is not None
        except Exception as e:
            logger.error(f"Error checking user existence for {user_id}: {e}")
            return False


# シングルトンファクトリ関数
_mock_user_service_instance = None

def get_mock_user_service() -> MockUserDataService:
    """MockUserDataService シングルトンインスタンス 取得"""
    global _mock_user_service_instance
    if _mock_user_service_instance is None:
        _mock_user_service_instance = MockUserDataService()
    return _mock_user_service_instance
