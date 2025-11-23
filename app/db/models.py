"""
PostgreSQL数据库模型定义
替代BigQuery和Firestore
"""
from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, JSON, ForeignKey, Index, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime

Base = declarative_base()


class User(Base):
    """用户表"""
    __tablename__ = "users"
    
    user_id = Column(String(50), primary_key=True)
    nickname = Column(String(100))
    email = Column(String(255), unique=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_active = Column(Boolean, default=True)
    
    # 关系
    portfolios = relationship("UserPortfolio", back_populates="user", cascade="all, delete-orphan")
    sessions = relationship("AISession", back_populates="user", cascade="all, delete-orphan")
    
    __table_args__ = (
        Index('idx_user_email', 'email'),
        Index('idx_user_created_at', 'created_at'),
    )


class UserPortfolio(Base):
    """用户资产组合"""
    __tablename__ = "user_portfolios"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String(50), ForeignKey('users.user_id'), nullable=False)
    asset_type = Column(String(50), nullable=False)  # POINTS, EARNINGS, CRYPTO, GIGA_ASSET等
    current_value = Column(Float, default=0.0)
    target_allocation = Column(Float, default=0.0)
    last_updated = Column(DateTime, default=datetime.utcnow)
    extra_data = Column(JSON, default={})
    
    # 关系
    user = relationship("User", back_populates="portfolios")
    
    __table_args__ = (
        Index('idx_portfolio_user_id', 'user_id'),
        Index('idx_portfolio_asset_type', 'asset_type'),
        Index('idx_portfolio_user_asset', 'user_id', 'asset_type'),
    )


class DailyUserBalance(Base):
    """每日用户余额 - 时序数据"""
    __tablename__ = "daily_user_balance"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String(50), ForeignKey('users.user_id'), nullable=False)
    date = Column(DateTime, nullable=False)
    freepoint_amount = Column(Float, default=0.0)
    prepaidpoint_amount = Column(Float, default=0.0)
    sales_amount = Column(Float, default=0.0)
    funds_amount = Column(Float, default=0.0)
    total_balance = Column(Float, default=0.0)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        Index('idx_balance_user_date', 'user_id', 'date'),
        Index('idx_balance_date', 'date'),
    )


class Transaction(Base):
    """交易记录"""
    __tablename__ = "transactions"
    
    transaction_id = Column(String(100), primary_key=True)
    user_id = Column(String(50), ForeignKey('users.user_id'))
    buyer_id = Column(String(50))
    seller_id = Column(String(50))
    item_id = Column(String(100))
    category_id = Column(Integer)
    price = Column(Float, nullable=False)
    status = Column(String(20))  # done, cancel, pending
    paid_method = Column(String(50))
    consume_point = Column(Float, default=0.0)
    consume_sales = Column(Float, default=0.0)
    created = Column(DateTime, default=datetime.utcnow)
    updated = Column(DateTime, default=datetime.utcnow)
    extra_data = Column(JSON, default={})
    
    __table_args__ = (
        Index('idx_transaction_user_id', 'user_id'),
        Index('idx_transaction_buyer_id', 'buyer_id'),
        Index('idx_transaction_seller_id', 'seller_id'),
        Index('idx_transaction_created', 'created'),
        Index('idx_transaction_status', 'status'),
    )


class AISession(Base):
    """AI会话记录"""
    __tablename__ = "ai_sessions"
    
    session_id = Column(String(100), primary_key=True)
    user_id = Column(String(50), ForeignKey('users.user_id'), nullable=False)
    session_type = Column(String(100))
    input_data = Column(JSON)
    ai_response = Column(JSON)
    user_feedback = Column(JSON)
    processing_time_ms = Column(Integer)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)
    
    # 关系
    user = relationship("User", back_populates="sessions")
    
    __table_args__ = (
        Index('idx_session_user_id', 'user_id'),
        Index('idx_session_created_at', 'created_at'),
        Index('idx_session_type', 'session_type'),
    )


class Recommendation(Base):
    """推荐记录"""
    __tablename__ = "recommendations"
    
    recommendation_id = Column(String(100), primary_key=True)
    user_id = Column(String(50), ForeignKey('users.user_id'), nullable=False)
    session_id = Column(String(100), ForeignKey('ai_sessions.session_id'))
    agent_name = Column(String(100))
    title = Column(String(255))
    description = Column(Text)
    asset_type = Column(String(50))
    potential_gain = Column(Float, default=0.0)
    priority = Column(Integer, default=0)
    status = Column(String(20))  # pending, accepted, rejected
    feedback = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        Index('idx_recommendation_user_id', 'user_id'),
        Index('idx_recommendation_status', 'status'),
        Index('idx_recommendation_session_id', 'session_id'),
    )


class UserFeedback(Base):
    """用户反馈"""
    __tablename__ = "user_feedback"
    
    feedback_id = Column(String(100), primary_key=True)
    user_id = Column(String(50), ForeignKey('users.user_id'), nullable=False)
    recommendation_id = Column(String(100), ForeignKey('recommendations.recommendation_id'))
    status = Column(String(20))  # accepted, rejected
    rejection_reason = Column(String(100))
    rejection_detail = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        Index('idx_feedback_user_id', 'user_id'),
        Index('idx_feedback_recommendation_id', 'recommendation_id'),
        Index('idx_feedback_created_at', 'created_at'),
    )


class AnalyticsCache(Base):
    """分析结果缓存"""
    __tablename__ = "analytics_cache"
    
    cache_id = Column(String(100), primary_key=True)
    cache_key = Column(String(255), unique=True, nullable=False)
    cache_type = Column(String(50))  # user_behavior, market_trends, etc.
    data = Column(JSON, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime)
    
    __table_args__ = (
        Index('idx_cache_key', 'cache_key'),
        Index('idx_cache_expires_at', 'expires_at'),
        Index('idx_cache_type', 'cache_type'),
    )

