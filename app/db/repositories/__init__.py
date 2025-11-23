"""
Data repository layer
Provides data access interfaces
"""
from app.db.repositories.user_repository import UserRepository
from app.db.repositories.analytics_repository import AnalyticsRepository

__all__ = ['UserRepository', 'AnalyticsRepository']

