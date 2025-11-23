"""
データサービスファクトリ

設定に基づいて適切なデータサービス実装を作成する責任を負います
"""

from typing import Dict, Any, Optional
import logging
from enum import Enum

from app.core.config import settings
from app.services.data.interfaces.user_data_interface import UserDataInterface
from app.services.data.interfaces.market_data_interface import MarketDataInterface
from app.services.data.interfaces.feedback_interface import FeedbackInterface

# Mock implementations (default)
from app.services.data.implementations.mock.mock_user_service import MockUserDataService
from app.services.data.implementations.mock.mock_market_service import MockMarketDataService
from app.services.data.implementations.mock.mock_feedback_service import MockFeedbackDataService


logger = logging.getLogger(__name__)


class DataSourceType(Enum):
    """データソースタイプ列挙"""
    MOCK = "mock"  # モックデータを使用


class DataServiceFactory:
    """
    データサービスファクトリクラス
    
    設定に基づいて対応するデータサービス実装を作成します
    """
    
    def __init__(self, data_source_type: Optional[DataSourceType] = None):
        """
        データサービスファクトリを初期化
        
        Args:
            data_source_type: データソースタイプ、Noneの場合は設定から読み取り
        """
        if data_source_type is None:
            # 設定ファイルからデータソースタイプを読み取り
            configured_type = getattr(settings, 'DATA_SOURCE_TYPE', 'mock')
            self.data_source_type = DataSourceType(configured_type.lower())
        else:
            self.data_source_type = data_source_type
            
        logger.info(f"DataServiceFactory initialized with source type: {self.data_source_type.value}")
        
        # サービスインスタンスをキャッシュ
        self._user_service: Optional[UserDataInterface] = None
        self._market_service: Optional[MarketDataInterface] = None  
        self._feedback_service: Optional[FeedbackInterface] = None
    
    def get_user_data_service(self) -> UserDataInterface:
        """ユーザーデータサービスインスタンスを取得"""
        if self._user_service is None:
            self._user_service = self._create_user_service()
        return self._user_service
    
    def get_market_data_service(self) -> MarketDataInterface:
        """市場データサービスインスタンスを取得"""
        if self._market_service is None:
            self._market_service = self._create_market_service()
        return self._market_service
    
    def get_feedback_service(self) -> FeedbackInterface:
        """フィードバックデータサービスインスタンスを取得"""
        if self._feedback_service is None:
            self._feedback_service = self._create_feedback_service()
        return self._feedback_service
    
    def _create_user_service(self) -> UserDataInterface:
        """ユーザーデータサービスインスタンスを作成"""
        logger.info("Creating MockUserDataService instance")
        return MockUserDataService()
    
    def _create_market_service(self) -> MarketDataInterface:
        """市場データサービスインスタンスを作成"""
        logger.info("Creating MockMarketDataService instance")
        return MockMarketDataService()
    
    def _create_feedback_service(self) -> FeedbackInterface:
        """フィードバックデータサービスインスタンスを作成"""
        logger.info("Creating MockFeedbackDataService instance")
        return MockFeedbackDataService()
    
    def switch_data_source(self, new_source_type: DataSourceType):
        """
        実行時にデータソースタイプを切り替え
        
        Args:
            new_source_type: 新しいデータソースタイプ
        """
        if new_source_type != self.data_source_type:
            logger.info(f"Switching data source from {self.data_source_type.value} to {new_source_type.value}")
            
            # 既存のサービスインスタンスをクリア
            self._user_service = None
            self._market_service = None
            self._feedback_service = None
            
            # データソースタイプを更新
            self.data_source_type = new_source_type
    
    def get_service_info(self) -> Dict[str, Any]:
        """
        現在のサービス設定情報を取得
        
        Returns:
            サービス設定情報の辞書
        """
        return {
            'data_source_type': self.data_source_type.value,
            'services': {
                'user_service': type(self.get_user_data_service()).__name__,
                'market_service': type(self.get_market_data_service()).__name__,
                'feedback_service': type(self.get_feedback_service()).__name__
            },
            'available_sources': [source.value for source in DataSourceType]
        }


# グローバルファクトリインスタンス
_data_service_factory: Optional[DataServiceFactory] = None


def get_data_service_factory() -> DataServiceFactory:
    """
    グローバルデータサービスファクトリインスタンスを取得
    
    Returns:
        DataServiceFactoryインスタンス
    """
    global _data_service_factory
    if _data_service_factory is None:
        _data_service_factory = DataServiceFactory()
    return _data_service_factory


def get_user_data_service() -> UserDataInterface:
    """ユーザーデータサービスインスタンスを取得するための便利なメソッド"""
    return get_data_service_factory().get_user_data_service()


def get_market_data_service() -> MarketDataInterface:
    """市場データサービスインスタンスを取得するための便利なメソッド"""
    return get_data_service_factory().get_market_data_service()


def get_feedback_service() -> FeedbackInterface:
    """フィードバックデータサービスインスタンスを取得するための便利なメソッド"""
    return get_data_service_factory().get_feedback_service()
