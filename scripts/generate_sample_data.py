#!/usr/bin/env python3
"""
Sample data generation script
Based on the original data_generation module structure, generates complete mock data for the open-source version
"""
import asyncio
import random
import uuid
from datetime import datetime, timedelta
from typing import List, Dict, Any
import sys
import os

# Add project root directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.db.database import init_db, get_db_session
from app.db.repositories.user_repository import UserRepository
from app.db.models import Transaction, AISession, Recommendation, UserFeedback


# Configuration constants
USER_IDS = list(range(1001, 1051))  # 50 users
DAYS_PERIOD = 90  # 90 days of historical data
ASSET_TYPES = ["POINTS", "EARNINGS", "CRYPTO", "GIGA_ASSET"]


class SampleDataGenerator:
    """Sample data generator"""
    
    def __init__(self):
        self.categories = [1, 2, 3, 4, 5, 6, 7, 8]  # Product categories
        self.payment_methods = ["credit_card", "points", "sales_balance", "mixed"]
        self.transaction_statuses = ["done", "pending", "cancelled"]
        
    def generate_user_id(self, index: int) -> str:
        """Generate user ID"""
        return f"user_{index}"
    
    def generate_transaction_id(self) -> str:
        """Generate transaction ID"""
        return f"txn_{uuid.uuid4().hex[:16]}"
    
    def generate_asset_value(self, asset_type: str) -> float:
        """Generate reasonable asset value based on asset type"""
        if asset_type == "POINTS":
            return random.uniform(5000, 100000)
        elif asset_type == "EARNINGS":
            return random.uniform(10000, 500000)
        elif asset_type == "CRYPTO":
            return random.uniform(1000, 50000)
        elif asset_type == "GIGA_ASSET":
            return random.uniform(500, 10000)
        return random.uniform(1000, 50000)
    
    def generate_asset_details(self, asset_type: str, value: float, allocation: float) -> Dict[str, Any]:
        """Generate asset additional information"""
        allocation_pct = round(allocation * 100, 2)
        timestamp = datetime.utcnow().isoformat()
        
        if asset_type == "POINTS":
            free_points = round(value * random.uniform(0.4, 0.7), 2)
            limited_points = round(value - free_points, 2)
            return {
                "asset_key": "points",
                "currency": "JPY",
                "last_synced_at": timestamp,
                "allocation_percentage": allocation_pct,
                "breakdown": {
                    "available_points": free_points,
                    "limited_time_points": limited_points,
                    "next_expiration": (datetime.utcnow() + timedelta(days=random.randint(15, 90))).isoformat()
                }
            }
        elif asset_type == "EARNINGS":
            auto_deposit = round(value * random.uniform(0.1, 0.3), 2)
            sales_balance = round(value - auto_deposit, 2)
            return {
                "asset_key": "earnings",
                "currency": "JPY",
                "last_synced_at": timestamp,
                "allocation_percentage": allocation_pct,
                "breakdown": {
                    "sales_balance": sales_balance,
                    "salary_balance": round(value * random.uniform(0.2, 0.4), 2),
                    "auto_deposit_reserve": auto_deposit
                }
            }
        elif asset_type == "CRYPTO":
            btc_value = round(value * random.uniform(0.4, 0.7), 2)
            eth_value = round(value * random.uniform(0.1, 0.3), 2)
            alt_value = round(value - btc_value - eth_value, 2)
            return {
                "asset_key": "stablecoin",
                "currency": "JPY",
                "last_synced_at": timestamp,
                "allocation_percentage": allocation_pct,
                "crypto_breakdown": {
                    "bitcoin": btc_value,
                    "ethereum": eth_value,
                    "altcoins": max(alt_value, 0.0)
                }
            }
        elif asset_type == "GIGA_ASSET":
            giga_balance = round(value * random.uniform(0.5, 0.8), 2)
            data_bonus = round(value - giga_balance, 2)
            return {
                "asset_key": "giga",
                "currency": "JPY",
                "last_synced_at": timestamp,
                "allocation_percentage": allocation_pct,
                "giga_summary": {
                    "giga_balance": giga_balance,
                    "bonus_awarded": data_bonus,
                    "monthly_plan": random.choice(["Light Plan", "Standard", "Premium"])
                }
            }
        else:
            return {
                "asset_key": asset_type.lower(),
                "currency": "JPY",
                "last_synced_at": timestamp,
                "allocation_percentage": allocation_pct
            }
    
    def generate_transaction(self, user_id: str, date: datetime) -> Dict[str, Any]:
        """Generate a transaction record"""
        is_buyer = random.choice([True, False])
        price = random.uniform(500, 50000)
        
        return {
            "transaction_id": self.generate_transaction_id(),
            "user_id": user_id,
            "buyer_id": user_id if is_buyer else f"user_{random.choice(USER_IDS)}",
            "seller_id": f"user_{random.choice(USER_IDS)}" if is_buyer else user_id,
            "item_id": f"item_{uuid.uuid4().hex[:12]}",
            "category_id": random.choice(self.categories),
            "price": price,
            "status": random.choice(self.transaction_statuses),
            "paid_method": random.choice(self.payment_methods),
            "consume_point": random.uniform(0, min(price * 0.3, 5000)),
            "consume_sales": random.uniform(0, min(price * 0.5, 10000)),
            "created": date,
            "updated": date,
            "metadata": {}
        }
    
    def generate_ai_session(self, user_id: str, date: datetime) -> Dict[str, Any]:
        """Generate AI session record"""
        session_types = ["portfolio_analysis", "recommendation_request", "risk_assessment"]
        
        return {
            "session_id": f"session_{uuid.uuid4().hex[:16]}",
            "user_id": user_id,
            "session_type": random.choice(session_types),
            "input_data": {
                "asset_types": ASSET_TYPES,
                "request_type": "analysis"
            },
            "ai_response": {
                "analysis": "Sample analysis result",
                "recommendations": []
            },
            "user_feedback": None if random.random() > 0.3 else {
                "rating": random.randint(3, 5),
                "helpful": random.choice([True, False])
            },
            "processing_time_ms": random.randint(500, 3000),
            "created_at": date,
            "updated_at": date
        }
    
    def generate_recommendation(self, user_id: str, session_id: str, date: datetime) -> Dict[str, Any]:
        """Generate recommendation record"""
        agents = ["PointsAnalyzer", "EarningsAnalyzer", "CryptoAnalyzer", "GIGAAnalyzer"]
        titles = [
            "Optimize Points Usage",
            "Rebalance Income Assets",
            "Diversify Cryptocurrency Investments",
            "Efficient GIGA Asset Utilization"
        ]
        
        return {
            "recommendation_id": f"rec_{uuid.uuid4().hex[:16]}",
            "user_id": user_id,
            "session_id": session_id,
            "agent_name": random.choice(agents),
            "title": random.choice(titles),
            "description": "Detailed recommendation content goes here",
            "asset_type": random.choice(ASSET_TYPES),
            "potential_gain": random.uniform(1000, 10000),
            "priority": random.randint(1, 5),
            "status": random.choice(["pending", "accepted", "rejected"]),
            "feedback": None,
            "created_at": date
        }


async def generate_users(repo: UserRepository, num_users: int = 50):
    """Generate user base data"""
    print(f"\n📝 Step 1/5: Generating {num_users} users...")
    
    generator = SampleDataGenerator()
    
    for i, user_index in enumerate(USER_IDS[:num_users]):
        user_id = generator.generate_user_id(user_index)
        nickname = f"User{user_index}"
        email = f"user{user_index}@example.com"
        
        try:
            user = await repo.get_or_create_user(user_id, nickname, email)
            if (i + 1) % 10 == 0:
                print(f"  ✅ Processed {i+1}/{num_users} users (current user: {user.user_id})")
            
        except Exception as e:
            print(f"  ⚠️  Failed to create user {user_id}: {e}")
    
    print(f"  ✅ Completed! Processed {num_users} users")


async def generate_assets(repo: UserRepository, num_users: int = 50):
    """Generate user asset data"""
    print(f"\n💰 Step 2/5: Generating portfolio data...")
    
    generator = SampleDataGenerator()
    total_assets = 0
    
    for i, user_index in enumerate(USER_IDS[:num_users]):
        user_id = generator.generate_user_id(user_index)
        
        # Create multiple asset types for each user
        for asset_type in ASSET_TYPES:
            value = generator.generate_asset_value(asset_type)
            allocation = random.uniform(0.15, 0.35)
            extra_data = generator.generate_asset_details(asset_type, value, allocation)
            
            try:
                await repo.update_user_asset(user_id, asset_type, value, allocation, extra_data=extra_data)
                total_assets += 1
            except Exception as e:
                print(f"  ⚠️  Failed to create asset {user_id}/{asset_type}: {e}")
        
        if (i + 1) % 10 == 0:
            print(f"  ✅ Processed assets for {i+1}/{num_users} users")
    
    print(f"  ✅ Completed! Created {total_assets} asset records")


async def generate_daily_balances(repo: UserRepository, num_users: int = 50):
    """Generate daily balance history"""
    print(f"\n📊 Step 3/5: Generating {DAYS_PERIOD} days of balance history...")
    
    generator = SampleDataGenerator()
    total_records = 0
    
    for i, user_index in enumerate(USER_IDS[:num_users]):
        user_id = generator.generate_user_id(user_index)
        
        # Generate daily balances for the past 90 days
        base_freepoint = random.uniform(10000, 80000)
        base_sales = random.uniform(5000, 50000)
        
        for days_ago in range(DAYS_PERIOD):
            date = datetime.utcnow() - timedelta(days=days_ago)
            
            # Add trend and random fluctuation
            trend = days_ago * random.uniform(-50, 100)
            fluctuation = random.uniform(0.8, 1.2)
            
            freepoint = max(0, (base_freepoint + trend) * fluctuation)
            prepaidpoint = random.uniform(0, 10000)
            sales = max(0, (base_sales + trend * 0.5) * fluctuation)
            funds = random.uniform(0, 20000)
            
            try:
                await repo.save_daily_balance(user_id, date, freepoint, prepaidpoint, sales, funds)
                total_records += 1
            except Exception as e:
                if days_ago == 0:  # Only print error for the first day
                    print(f"  ⚠️  Failed to save balance record {user_id}: {e}")
        
        if (i + 1) % 10 == 0:
            print(f"  ✅ Processed historical data for {i+1}/{num_users} users")
    
    print(f"  ✅ Completed! Created {total_records} balance records")


async def generate_transactions(session, num_users: int = 50):
    """Generate transaction records"""
    print(f"\n💳 Step 4/5: Generating transaction records...")
    
    generator = SampleDataGenerator()
    total_transactions = 0
    
    for i, user_index in enumerate(USER_IDS[:num_users]):
        user_id = generator.generate_user_id(user_index)
        
        # Generate 20-50 transactions per user
        num_transactions = random.randint(20, 50)
        
        for _ in range(num_transactions):
            # Randomly distributed over the past 90 days
            days_ago = random.randint(0, DAYS_PERIOD - 1)
            date = datetime.utcnow() - timedelta(days=days_ago)
            
            transaction_data = generator.generate_transaction(user_id, date)
            transaction = Transaction(**transaction_data)
            
            try:
                session.add(transaction)
                total_transactions += 1
            except Exception as e:
                print(f"  ⚠️  Failed to create transaction record: {e}")
        
        if (i + 1) % 10 == 0:
            print(f"  ✅ Processed transactions for {i+1}/{num_users} users")
    
    await session.commit()
    print(f"  ✅ Completed! Created {total_transactions} transaction records")


async def generate_ai_data(session, num_users: int = 50):
    """Generate AI session and recommendation data"""
    print(f"\n🤖 Step 5/5: Generating AI sessions and recommendations...")
    
    generator = SampleDataGenerator()
    total_sessions = 0
    total_recommendations = 0
    
    for i, user_index in enumerate(USER_IDS[:num_users]):
        user_id = generator.generate_user_id(user_index)
        
        # Generate 5-15 AI sessions per user
        num_sessions = random.randint(5, 15)
        
        for _ in range(num_sessions):
            days_ago = random.randint(0, DAYS_PERIOD - 1)
            date = datetime.utcnow() - timedelta(days=days_ago)
            
            # Create AI session
            session_data = generator.generate_ai_session(user_id, date)
            ai_session = AISession(
                session_id=session_data["session_id"],
                user_id=session_data["user_id"],
                session_type=session_data["session_type"],
                input_data=str(session_data["input_data"]),
                ai_response=str(session_data["ai_response"]),
                user_feedback=str(session_data["user_feedback"]) if session_data["user_feedback"] else None,
                processing_time_ms=session_data["processing_time_ms"],
                created_at=session_data["created_at"],
                updated_at=session_data["updated_at"]
            )
            
            try:
                session.add(ai_session)
                total_sessions += 1
                
                # Generate 1-3 recommendations per session
                num_recommendations = random.randint(1, 3)
                for _ in range(num_recommendations):
                    rec_data = generator.generate_recommendation(
                        user_id, session_data["session_id"], date
                    )
                    recommendation = Recommendation(**rec_data)
                    session.add(recommendation)
                    total_recommendations += 1
                    
            except Exception as e:
                print(f"  ⚠️  Failed to create AI data: {e}")
        
        if (i + 1) % 10 == 0:
            print(f"  ✅ Processed AI data for {i+1}/{num_users} users")
    
    await session.commit()
    print(f"  ✅ Completed! Created {total_sessions} sessions and {total_recommendations} recommendations")


async def main():
    """Main function"""
    print("=" * 60)
    print("  💰 Saving Advisor System - Sample Data Generator")
    print("=" * 60)
    print()
    print("📋 Generation Plan:")
    print(f"  - Number of users: 50")
    print(f"  - Asset types: {len(ASSET_TYPES)} types")
    print(f"  - Historical period: {DAYS_PERIOD} days")
    print(f"  - Estimated records: ~10,000+ records")
    print()
    
    # Initialize database
    print("🔧 Initializing database...")
    try:
        await init_db()
        print("  ✅ Database initialization successful\n")
    except Exception as e:
        print(f"  ❌ Database initialization failed: {e}")
        return
    
    # Start generating data
    start_time = datetime.now()
    
    async with get_db_session() as db_session:
        repo = UserRepository(db_session)
        
        # Step 1: Users
        await generate_users(repo, num_users=50)
        await db_session.commit()
        
        # Step 2: Assets
        await generate_assets(repo, num_users=50)
        await db_session.commit()
        
        # Step 3: Daily balances
        await generate_daily_balances(repo, num_users=50)
        await db_session.commit()
        
        # Step 4: Transactions
        await generate_transactions(db_session, num_users=50)
        
        # Step 5: AI data
        await generate_ai_data(db_session, num_users=50)
    
    elapsed = (datetime.now() - start_time).total_seconds()
    
    print()
    print("=" * 60)
    print(f"  🎉 Data generation completed! Took {elapsed:.2f} seconds")
    print("=" * 60)
    print()
    print("📊 Data Statistics:")
    print(f"  ✓ Users: 50")
    print(f"  ✓ Asset records: ~200")
    print(f"  ✓ Daily balances: ~4,500")
    print(f"  ✓ Transaction records: ~1,500")
    print(f"  ✓ AI sessions: ~500")
    print(f"  ✓ Recommendation records: ~1,000")
    print()
    print("🚀 You can now start the application:")
    print("  uvicorn app.main:app --reload")
    print("  or use Docker: docker-compose up")
    print()


if __name__ == "__main__":
    asyncio.run(main())
