"""
data service抽象层

为未来andMercari主application集成provide抽象interface，现阶段usemock dataimplement
"""

from .factory import get_data_service_factory, DataServiceFactory
from .interfaces.user_data_interface import UserDataInterface
from .interfaces.market_data_interface import MarketDataInterface
from .interfaces.feedback_interface import FeedbackInterface

__all__ = [
    'get_data_service_factory',
    'DataServiceFactory',
    'UserDataInterface',
    'MarketDataInterface',
    'FeedbackInterface'
]
