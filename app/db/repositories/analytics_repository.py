"""
Analytics data repository
Replaces BigQuery analytics functionality
"""
from sqlalchemy import select, and_, func, case, or_
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any, List
from datetime import datetime, timedelta

from app.db.models import User, Transaction, AISession, Recommendation, DailyUserBalance


class AnalyticsRepository:
    """Analytics data repository"""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def get_user_behavior_analysis(self, user_id: str) -> Dict[str, Any]:
        """User behavior analysis"""
        # Transaction statistics
        transaction_stats = await self.session.execute(
            select(
                func.count(Transaction.transaction_id).label('total_transactions'),
                func.avg(Transaction.price).label('avg_transaction_value'),
                func.sum(Transaction.price).label('total_transaction_value'),
                func.count(case((Transaction.buyer_id == user_id, 1))).label('buyer_transactions'),
                func.count(case((Transaction.seller_id == user_id, 1))).label('seller_transactions'),
            )
            .where(
                or_(
                    Transaction.buyer_id == user_id,
                    Transaction.seller_id == user_id
                )
            )
        )
        trans_stats = transaction_stats.one()
        
        # AI会话统计
        ai_stats = await self.session.execute(
            select(
                func.count(AISession.session_id).label('session_count'),
                func.count(case((AISession.user_feedback.isnot(None), 1))).label('feedback_count'),
            )
            .where(
                and_(
                    AISession.user_id == user_id,
                    AISession.created_at >= datetime.utcnow() - timedelta(days=30)
                )
            )
        )
        ai_data = ai_stats.one()
        
        # Asset statistics
        balance_stats = await self.session.execute(
            select(
                func.avg(DailyUserBalance.total_balance).label('avg_balance'),
                func.max(DailyUserBalance.total_balance).label('max_balance'),
                func.min(DailyUserBalance.total_balance).label('min_balance'),
            )
            .where(
                and_(
                    DailyUserBalance.user_id == user_id,
                    DailyUserBalance.date >= datetime.utcnow() - timedelta(days=30)
                )
            )
        )
        balance_data = balance_stats.one()
        
        return {
            'total_transactions': trans_stats.total_transactions or 0,
            'avg_transaction_value': float(trans_stats.avg_transaction_value or 0),
            'total_transaction_value': float(trans_stats.total_transaction_value or 0),
            'buyer_transactions': trans_stats.buyer_transactions or 0,
            'seller_transactions': trans_stats.seller_transactions or 0,
            'ai_session_count': ai_data.session_count or 0,
            'feedback_count': ai_data.feedback_count or 0,
            'avg_balance': float(balance_data.avg_balance or 0),
            'max_balance': float(balance_data.max_balance or 0),
            'min_balance': float(balance_data.min_balance or 0),
        }
    
    async def get_market_trends(self, days: int = 30) -> Dict[str, Any]:
        """Market trend analysis"""
        start_date = datetime.utcnow() - timedelta(days=days)
        
        # Statistics by date
        daily_stats = await self.session.execute(
            select(
                func.date(Transaction.created).label('date'),
                func.count(Transaction.transaction_id).label('transaction_count'),
                func.avg(Transaction.price).label('avg_price'),
                func.sum(Transaction.price).label('total_value'),
            )
            .where(Transaction.created >= start_date)
            .group_by(func.date(Transaction.created))
            .order_by(func.date(Transaction.created))
        )
        
        trends = []
        for row in daily_stats:
            trends.append({
                'date': row.date.isoformat() if hasattr(row.date, 'isoformat') else str(row.date),
                'transaction_count': row.transaction_count or 0,
                'avg_price': float(row.avg_price or 0),
                'total_value': float(row.total_value or 0),
            })
        
        return {
            'period_days': days,
            'trends': trends,
            'start_date': start_date.isoformat(),
            'end_date': datetime.utcnow().isoformat(),
        }
    
    async def get_recommendation_performance(self) -> Dict[str, Any]:
        """Recommendation system effectiveness analysis"""
        # Recommendation statistics
        rec_stats = await self.session.execute(
            select(
                func.count(Recommendation.recommendation_id).label('total_recommendations'),
                func.count(case((Recommendation.status == 'accepted', 1))).label('accepted'),
                func.count(case((Recommendation.status == 'rejected', 1))).label('rejected'),
                func.count(case((Recommendation.status == 'pending', 1))).label('pending'),
            )
            .where(
                Recommendation.created_at >= datetime.utcnow() - timedelta(days=30)
            )
        )
        stats = rec_stats.one()
        
        total = stats.total_recommendations or 0
        acceptance_rate = (stats.accepted / total * 100) if total > 0 else 0.0
        
        return {
            'total_recommendations': total,
            'accepted': stats.accepted or 0,
            'rejected': stats.rejected or 0,
            'pending': stats.pending or 0,
            'acceptance_rate': acceptance_rate,
            'analysis_period': '30 days',
        }
    
    async def get_user_engagement_metrics(self) -> Dict[str, Any]:
        """User engagement metrics"""
        # Active user statistics
        active_users = await self.session.execute(
            select(func.count(func.distinct(AISession.user_id)))
            .where(AISession.created_at >= datetime.utcnow() - timedelta(days=7))
        )
        weekly_active = active_users.scalar() or 0
        
        active_users_monthly = await self.session.execute(
            select(func.count(func.distinct(AISession.user_id)))
            .where(AISession.created_at >= datetime.utcnow() - timedelta(days=30))
        )
        monthly_active = active_users_monthly.scalar() or 0
        
        # Total user count
        total_users = await self.session.execute(
            select(func.count(User.user_id))
        )
        total = total_users.scalar() or 0
        
        return {
            'total_users': total,
            'weekly_active_users': weekly_active,
            'monthly_active_users': monthly_active,
            'weekly_engagement_rate': (weekly_active / total * 100) if total > 0 else 0.0,
            'monthly_engagement_rate': (monthly_active / total * 100) if total > 0 else 0.0,
        }

