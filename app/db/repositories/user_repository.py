"""
User data repository
Provides CRUD operations for user and asset data
"""
from sqlalchemy import select, and_, or_, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
import uuid

from app.db.models import User, UserPortfolio, DailyUserBalance, Transaction


class UserRepository:
    """User data repository"""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def get_user(self, user_id: str) -> Optional[User]:
        """Get user"""
        result = await self.session.execute(
            select(User).where(User.user_id == user_id)
        )
        return result.scalar_one_or_none()
    
    async def create_user(self, user_id: str, nickname: str, email: str) -> User:
        """Create user"""
        user = User(
            user_id=user_id,
            nickname=nickname,
            email=email,
            created_at=datetime.utcnow()
        )
        self.session.add(user)
        await self.session.flush()
        return user
    
    async def get_or_create_user(self, user_id: str, nickname: str = None, email: str = None) -> User:
        """Get or create user"""
        user = await self.get_user(user_id)
        if not user:
            if not nickname:
                nickname = f"User{user_id}"
            if not email:
                email = f"user_{user_id}@example.com"
            user = await self.create_user(user_id, nickname, email)
        return user
    
    async def get_user_portfolio(self, user_id: str) -> List[UserPortfolio]:
        """Get user portfolio"""
        result = await self.session.execute(
            select(UserPortfolio)
            .where(UserPortfolio.user_id == user_id)
            .order_by(UserPortfolio.asset_type)
        )
        return list(result.scalars().all())
    
    async def update_user_asset(
        self,
        user_id: str,
        asset_type: str,
        current_value: float,
        target_allocation: float = None,
        extra_data: Optional[Dict[str, Any]] = None,
    ) -> UserPortfolio:
        """Update user asset"""
        # Find existing asset
        result = await self.session.execute(
            select(UserPortfolio).where(
                and_(
                    UserPortfolio.user_id == user_id,
                    UserPortfolio.asset_type == asset_type
                )
            )
        )
        portfolio = result.scalar_one_or_none()
        
        if portfolio:
            # Update existing asset
            portfolio.current_value = current_value
            if target_allocation is not None:
                portfolio.target_allocation = target_allocation
            portfolio.last_updated = datetime.utcnow()
            if extra_data is not None:
                portfolio.extra_data = extra_data
        else:
            # Create new asset
            portfolio = UserPortfolio(
                user_id=user_id,
                asset_type=asset_type,
                current_value=current_value,
                target_allocation=target_allocation or 0.0,
                last_updated=datetime.utcnow(),
                extra_data=extra_data or {},
            )
            self.session.add(portfolio)
        
        await self.session.flush()
        return portfolio
    
    async def get_daily_balance_history(
        self,
        user_id: str,
        days: int = 30
    ) -> List[DailyUserBalance]:
        """Get user daily balance history"""
        start_date = datetime.utcnow() - timedelta(days=days)
        
        result = await self.session.execute(
            select(DailyUserBalance)
            .where(
                and_(
                    DailyUserBalance.user_id == user_id,
                    DailyUserBalance.date >= start_date
                )
            )
            .order_by(DailyUserBalance.date.desc())
        )
        return list(result.scalars().all())
    
    async def save_daily_balance(
        self,
        user_id: str,
        date: datetime,
        freepoint: float,
        prepaidpoint: float,
        sales: float,
        funds: float
    ) -> DailyUserBalance:
        """Save daily balance"""
        total = freepoint + prepaidpoint + sales + funds
        
        # Check if already exists
        result = await self.session.execute(
            select(DailyUserBalance).where(
                and_(
                    DailyUserBalance.user_id == user_id,
                    func.date(DailyUserBalance.date) == date.date()
                )
            )
        )
        balance = result.scalar_one_or_none()
        
        if balance:
            # Update
            balance.freepoint_amount = freepoint
            balance.prepaidpoint_amount = prepaidpoint
            balance.sales_amount = sales
            balance.funds_amount = funds
            balance.total_balance = total
        else:
            # Create
            balance = DailyUserBalance(
                user_id=user_id,
                date=date,
                freepoint_amount=freepoint,
                prepaidpoint_amount=prepaidpoint,
                sales_amount=sales,
                funds_amount=funds,
                total_balance=total,
                created_at=datetime.utcnow()
            )
            self.session.add(balance)
        
        await self.session.flush()
        return balance
    
    async def get_user_transactions(
        self,
        user_id: str,
        limit: int = 100
    ) -> List[Transaction]:
        """Get user transactions"""
        result = await self.session.execute(
            select(Transaction)
            .where(
                or_(
                    Transaction.buyer_id == user_id,
                    Transaction.seller_id == user_id
                )
            )
            .order_by(Transaction.created.desc())
            .limit(limit)
        )
        return list(result.scalars().all())
    
    async def save_transaction(self, transaction_data: Dict[str, Any]) -> Transaction:
        """Save transaction"""
        transaction_id = transaction_data.get('transaction_id', str(uuid.uuid4()))
        
        # Check if already exists
        result = await self.session.execute(
            select(Transaction).where(Transaction.transaction_id == transaction_id)
        )
        transaction = result.scalar_one_or_none()
        
        if transaction:
            # Update
            for key, value in transaction_data.items():
                if hasattr(transaction, key):
                    setattr(transaction, key, value)
        else:
            # Create
            transaction = Transaction(transaction_id=transaction_id, **transaction_data)
            self.session.add(transaction)
        
        await self.session.flush()
        return transaction
    
    async def get_user_asset_statistics(self, user_id: str) -> Dict[str, Any]:
        """Get user asset statistics"""
        # Get total assets
        result = await self.session.execute(
            select(func.sum(UserPortfolio.current_value))
            .where(UserPortfolio.user_id == user_id)
        )
        total_value = result.scalar() or 0.0
        
        # Get asset count
        result = await self.session.execute(
            select(func.count(UserPortfolio.id))
            .where(UserPortfolio.user_id == user_id)
        )
        asset_count = result.scalar() or 0
        
        # Get last 30 days growth
        result = await self.session.execute(
            select(DailyUserBalance.total_balance)
            .where(
                and_(
                    DailyUserBalance.user_id == user_id,
                    DailyUserBalance.date >= datetime.utcnow() - timedelta(days=30)
                )
            )
            .order_by(DailyUserBalance.date.asc())
            .limit(1)
        )
        balance_30_days_ago = result.scalar() or 0.0
        
        growth = total_value - balance_30_days_ago if balance_30_days_ago > 0 else 0.0
        growth_rate = (growth / balance_30_days_ago * 100) if balance_30_days_ago > 0 else 0.0
        
        return {
            "total_value": total_value,
            "asset_count": asset_count,
            "30_day_growth": growth,
            "30_day_growth_rate": growth_rate
        }

