"""
Open-source implementation of the former Firestore primary service.

The original project stored user-facing data in Firestore. For the open-source
version we persist the same logical entities in PostgreSQL via SQLAlchemy.  This
module provides a drop-in replacement that keeps the public API identical while
fetching and storing data inside the relational database.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta
import uuid
import logging

from fastapi import HTTPException
from sqlalchemy import select, desc, func
from fastapi.encoders import jsonable_encoder

from app.db.database import get_db_session
from app.db.repositories.user_repository import UserRepository
from app.db.models import (
    AISession,
    Recommendation,
    UserFeedback,
    User,
    Transaction,
    DailyUserBalance,
)
from app.models.assets import (
    UserPortfolio as PortfolioModel,
    UserAsset,
    AssetType,
    RiskLevel,
)

logger = logging.getLogger(__name__)


# 映射旧的Firestore资产键到新的PostgreSQL资产类型
ASSET_KEY_MAPPING = {
    "POINTS": "points",
    "EARNINGS": "earnings",
    "CRYPTO": "stablecoin",
    "CRYPTO_ASSET": "stablecoin",
    "STABLECOIN": "stablecoin",
    "ITEMS": "items",
    "GIGA": "giga",
    "GIGA_ASSET": "giga",
}


def _default_asset_bucket(asset_key: str) -> Dict[str, Any]:
    """Create an empty asset bucket for the given logical key."""
    return {
        "asset_key": asset_key,
        "estimated_value": 0.0,
        "target_allocation": 0.0,
        "last_updated": None,
        "details": {},
    }


class FirestorePrimaryService:
    """
    Replacement service that mirrors the original Firestore API.
    All reads and writes are backed by the PostgreSQL database.
    """

    def __init__(self) -> None:
        self._logger = logger

    async def _fetch_portfolio_rows(self, user_id: str):
        async with get_db_session() as session:
            repo = UserRepository(session)
            return await repo.get_user_portfolio(user_id)

    async def _resolve_user_id(self, user_id: str):
        rows = await self._fetch_portfolio_rows(user_id)
        if rows:
            return user_id, rows

        if not user_id.startswith("user_"):
            alt_user_id = f"user_{user_id}"
            rows = await self._fetch_portfolio_rows(alt_user_id)
            if rows:
                return alt_user_id, rows

        return user_id, []

    async def _normalize_user_id(self, user_id: str) -> str:
        """
        Ensure we use the stored primary key format (e.g. user_1001).
        If the user does not exist, create a placeholder entry to satisfy FK constraints.
        """
        async with get_db_session() as session:
            repo = UserRepository(session)

            existing_user = await repo.get_user(user_id)
            if existing_user:
                return existing_user.user_id

            if not user_id.startswith("user_"):
                alt_user_id = f"user_{user_id}"
                existing_alt = await repo.get_user(alt_user_id)
                if existing_alt:
                    return existing_alt.user_id

                # Create placeholder user to satisfy FK relationships
                nickname = f"User{user_id}"
                email = f"user{user_id}@example.com"
                new_user = await repo.get_or_create_user(alt_user_id, nickname, email)
                return new_user.user_id

            # If the provided ID already has prefix but doesn't exist, create it as well
            nickname = f"User{user_id.replace('user_', '')}"
            email = f"{user_id}@example.com"
            new_user = await repo.get_or_create_user(user_id, nickname, email)
            return new_user.user_id

    # ------------------------------------------------------------------
    # Asset & portfolio helpers
    # ------------------------------------------------------------------
    async def get_user_current_assets(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Return the latest asset snapshot for a user.

        The result mimics the structure produced by the former Firestore
        document so that downstream code (models, view layer, agents) can stay
        untouched.
        """
        resolved_user_id, portfolio_rows = await self._resolve_user_id(user_id)
        if not portfolio_rows:
            self._logger.info("No portfolio data for user %s", user_id)
            return None

        result: Dict[str, Dict[str, Any]] = {
            "points": _default_asset_bucket("points"),
            "earnings": _default_asset_bucket("earnings"),
            "items": _default_asset_bucket("items"),
            "giga": _default_asset_bucket("giga"),
            "stablecoin": _default_asset_bucket("stablecoin"),
        }

        total_value = 0.0
        for row in portfolio_rows:
            asset_key = ASSET_KEY_MAPPING.get(row.asset_type.upper(), row.asset_type.lower())
            bucket = result.setdefault(asset_key, _default_asset_bucket(asset_key))
            bucket["estimated_value"] = float(row.current_value or 0.0)
            bucket["target_allocation"] = float(row.target_allocation or 0.0)
            bucket["last_updated"] = row.last_updated.isoformat() if row.last_updated else None
            bucket["details"] = row.extra_data or {}
            total_value += float(row.current_value or 0.0)

        result["summary"] = {
            "total_value": total_value,
            "asset_count": len(portfolio_rows),
            "resolved_user_id": resolved_user_id,
        }
        return result

    async def get_user_portfolio(
        self,
        user_id: str,
        allow_empty: bool = False,
        raise_http_exception: bool = False,
    ) -> Optional[PortfolioModel]:
        """
        Build a `UserPortfolio` Pydantic model from the relational data.
        """
        asset_snapshot = await self.get_user_current_assets(user_id)
        if not asset_snapshot:
            if allow_empty:
                return PortfolioModel(user_id=user_id, total_assets=0.0, assets=[])
            if raise_http_exception:
                raise HTTPException(status_code=404, detail="User portfolio not found")
            return None

        resolved_user_id = asset_snapshot.get("summary", {}).get("resolved_user_id") or user_id

        assets: List[UserAsset] = []
        total_value = 0.0
        type_mapping = {
            "points": AssetType.POINTS,
            "earnings": AssetType.EARNINGS,
            "items": AssetType.ITEMS,
            "giga": AssetType.GIGA,
            "stablecoin": AssetType.STABLECOIN,
        }

        for key, asset_type in type_mapping.items():
            data = asset_snapshot.get(key, {})
            value = float(data.get("estimated_value", 0.0))
            total_value += value
            metadata = data.get("details") or {}
            assets.append(
                UserAsset(
                    user_id=resolved_user_id,
                    asset_type=asset_type,
                    current_value=value,
                    metadata=metadata,
                )
            )

        return PortfolioModel(
            user_id=resolved_user_id,
            total_assets=total_value,
            assets=assets,
            risk_profile=RiskLevel.MEDIUM,
            last_analyzed=datetime.utcnow(),
        )

    # ------------------------------------------------------------------
    # AI session helpers
    # ------------------------------------------------------------------
    async def get_recent_ai_analysis(
        self,
        user_id: str,
        session_type: str = "portfolio_analysis",
        max_age_hours: int = 12,
    ) -> Optional[Dict[str, Any]]:
        """
        Fetch the most recent AI session of the given type within the age window.
        """
        time_threshold = datetime.utcnow() - timedelta(hours=max_age_hours)
        normalized_user_id = await self._normalize_user_id(user_id)

        async with get_db_session() as session:
            result = await session.execute(
                select(AISession)
                .where(
                    AISession.user_id == normalized_user_id,
                    AISession.session_type == session_type,
                    AISession.created_at >= time_threshold,
                )
                .order_by(desc(AISession.created_at))
                .limit(1)
            )
            session_row = result.scalar_one_or_none()

        if not session_row:
            return None

        return {
            "session_id": session_row.session_id,
            "user_id": session_row.user_id,
            "session_type": session_row.session_type,
            "input_data": session_row.input_data or {},
            "ai_response": session_row.ai_response or {},
            "processing_time_ms": session_row.processing_time_ms,
            "created_at": session_row.created_at.isoformat() if session_row.created_at else None,
            "updated_at": session_row.updated_at.isoformat() if session_row.updated_at else None,
        }

    async def save_ai_analysis(
        self,
        user_id: str,
        session_type: str,
        input_data: Dict[str, Any],
        ai_response: Dict[str, Any],
        processing_time_ms: int,
    ) -> str:
        """
        Persist an AI analysis session and return its identifier.
        """
        return await self.save_ai_session(
            user_id=user_id,
            session_type=session_type,
            input_data=input_data,
            ai_response=ai_response,
            processing_time_ms=processing_time_ms,
            user_feedback=None,
        )

    async def save_ai_session(
        self,
        user_id: str,
        session_type: str,
        input_data: Dict[str, Any],
        ai_response: Dict[str, Any],
        processing_time_ms: Optional[int] = None,
        user_feedback: Optional[Dict[str, Any]] = None,
    ) -> str:
        session_id = f"{session_type}_{uuid.uuid4().hex[:12]}"

        input_json = jsonable_encoder(input_data)
        response_json = jsonable_encoder(ai_response)
        feedback_json = jsonable_encoder(user_feedback) if user_feedback is not None else None

        normalized_user_id = await self._normalize_user_id(user_id)

        new_session = AISession(
            session_id=session_id,
            user_id=normalized_user_id,
            session_type=session_type,
            input_data=input_json,
            ai_response=response_json,
            user_feedback=feedback_json,
            processing_time_ms=processing_time_ms,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )

        async with get_db_session() as session:
            session.add(new_session)
            await session.flush()

        return session_id

    # ------------------------------------------------------------------
    # Recommendation & feedback helpers
    # ------------------------------------------------------------------
    async def save_recommendation_feedback(self, feedback_data: Dict[str, Any]) -> Optional[str]:
        """
        Store user feedback for a recommendation.
        """
        feedback_id = feedback_data.get("feedback_id") or f"fb_{uuid.uuid4().hex[:16]}"
        created_at = datetime.utcnow()
        normalized_user_id = await self._normalize_user_id(feedback_data.get("user_id"))

        record = UserFeedback(
            feedback_id=feedback_id,
            user_id=normalized_user_id,
            recommendation_id=feedback_data.get("recommendation_id"),
            status=feedback_data.get("status"),
            rejection_reason=feedback_data.get("rejection_reason"),
            rejection_detail=feedback_data.get("rejection_detail"),
            created_at=created_at,
        )

        async with get_db_session() as session:
            if feedback_data.get("recommendation_id"):
                recommendation = await session.get(
                    Recommendation, feedback_data["recommendation_id"]
                )
                if recommendation is None:
                    self._logger.warning(
                        "Feedback refers to non-existent recommendation %s. Removing recommendation_id to avoid FK error.",
                        feedback_data["recommendation_id"],
                    )
                    record.recommendation_id = None

            session.add(record)
            await session.flush()
            await session.commit()

        return feedback_id

    async def get_user_feedback_history(self, user_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        normalized_user_id = await self._normalize_user_id(user_id)
        async with get_db_session() as session:
            result = await session.execute(
                select(UserFeedback)
                .where(UserFeedback.user_id == normalized_user_id)
                .order_by(desc(UserFeedback.created_at))
                .limit(limit)
            )
            rows = list(result.scalars())

        history: List[Dict[str, Any]] = []
        for row in rows:
            history.append(
                {
                    "feedback_id": row.feedback_id,
                    "user_id": row.user_id,
                    "recommendation_id": row.recommendation_id,
                    "status": row.status,
                    "rejection_reason": row.rejection_reason,
                    "rejection_detail": row.rejection_detail,
                    "created_at": row.created_at.isoformat() if row.created_at else None,
                }
            )
        return history

    async def get_user_recommendations(self, user_id: str, limit: int = 20) -> List[Dict[str, Any]]:
        normalized_user_id = await self._normalize_user_id(user_id)

        async with get_db_session() as session:
            result = await session.execute(
                select(Recommendation)
                .where(Recommendation.user_id == normalized_user_id)
                .order_by(desc(Recommendation.created_at))
                .limit(limit)
            )
            rows = list(result.scalars())

        recommendations: List[Dict[str, Any]] = []
        for row in rows:
            recommendations.append(
                {
                    "recommendation_id": row.recommendation_id,
                    "user_id": row.user_id,
                    "session_id": row.session_id,
                    "agent_name": row.agent_name,
                    "title": row.title,
                    "description": row.description,
                    "asset_type": row.asset_type,
                    "potential_gain": row.potential_gain,
                    "priority": row.priority,
                    "status": row.status,
                    "feedback": row.feedback,
                    "created_at": row.created_at.isoformat() if row.created_at else None,
                }
            )
        return recommendations

    async def update_recommendation_status(
        self,
        recommendation_id: str,
        status: str,
        feedback: Optional[Dict[str, Any]] = None,
    ) -> bool:
        async with get_db_session() as session:
            result = await session.execute(
                select(Recommendation).where(Recommendation.recommendation_id == recommendation_id)
            )
            recommendation = result.scalar_one_or_none()
            if not recommendation:
                return False

            recommendation.status = status
            recommendation.feedback = feedback
            recommendation.created_at = recommendation.created_at or datetime.utcnow()
            await session.flush()
        return True

    async def save_recommendation_session(
        self,
        user_id: str,
        session_data: Dict[str, Any],
    ) -> str:
        """
        Historical compatibility wrapper – stored as a generic AI session.
        """
        return await self.save_ai_session(
            user_id=user_id,
            session_type=session_data.get("session_type", "recommendation_session"),
            input_data=session_data.get("input_data", {}),
            ai_response=session_data.get("ai_response", {}),
            processing_time_ms=session_data.get("processing_time_ms"),
            user_feedback=session_data.get("user_feedback"),
        )

    async def get_recommendation_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        async with get_db_session() as session:
            result = await session.execute(
                select(AISession).where(AISession.session_id == session_id)
            )
            session_row = result.scalar_one_or_none()

        if not session_row:
            return None

        return {
            "session_id": session_row.session_id,
            "user_id": session_row.user_id,
            "session_type": session_row.session_type,
            "input_data": session_row.input_data or {},
            "ai_response": session_row.ai_response or {},
            "user_feedback": session_row.user_feedback or {},
            "processing_time_ms": session_row.processing_time_ms,
            "created_at": session_row.created_at.isoformat() if session_row.created_at else None,
        }

    async def get_user_recommendation_history(self, user_id: str, limit: int = 20) -> List[Dict[str, Any]]:
        """
        Combine recommendations and feedback for history display.
        """
        recommendations = await self.get_user_recommendations(user_id, limit=limit)
        feedback_lookup = {
            fb["recommendation_id"]: fb for fb in await self.get_user_feedback_history(user_id, limit=limit * 2)
        }

        history: List[Dict[str, Any]] = []
        for rec in recommendations:
            entry = {
                **rec,
                "feedback": feedback_lookup.get(rec["recommendation_id"]),
            }
            history.append(entry)
        return history

    # ------------------------------------------------------------------
    # User profile helpers
    # ------------------------------------------------------------------
    async def get_user_profile(self, user_id: str) -> Optional[Dict[str, Any]]:
        async with get_db_session() as session:
            result = await session.execute(select(User).where(User.user_id == user_id))
            user = result.scalar_one_or_none()

        if not user:
            return None

        return {
            "user_id": user.user_id,
            "nickname": user.nickname,
            "email": user.email,
            "created_at": user.created_at.isoformat() if user.created_at else None,
            "updated_at": user.updated_at.isoformat() if user.updated_at else None,
        }

    async def get_user_risk_profile(self, user_id: str) -> Dict[str, Any]:
        """
        Compute a very lightweight risk profile derived from portfolio spread.
        """
        asset_snapshot = await self.get_user_current_assets(user_id) or {}
        summary = asset_snapshot.get("summary", {})
        total = summary.get("total_value", 0.0) or 0.0

        if total <= 0:
            risk_level = "unknown"
        else:
            # 如果加密资产占比高，则风险较高
            crypto_ratio = (asset_snapshot.get("stablecoin", {}).get("estimated_value", 0.0)) / total
            earnings_ratio = (asset_snapshot.get("earnings", {}).get("estimated_value", 0.0)) / total
            if crypto_ratio > 0.3:
                risk_level = "aggressive"
            elif earnings_ratio > 0.5:
                risk_level = "conservative"
            else:
                risk_level = "moderate"

        return {
            "user_id": user_id,
            "risk_level": risk_level,
            "risk_score": 65 if risk_level == "moderate" else (80 if risk_level == "aggressive" else 45),
            "liquidity_preference": "medium",
            "investment_tendency": "investor" if risk_level == "aggressive" else "saver",
            "recommended_asset_allocation": {
                "points": 0.25,
                "earnings": 0.35,
                "stablecoin": 0.20,
                "items": 0.10,
                "giga": 0.10,
            },
            "risk_warnings": [
                "多様な資産クラスへの配分を継続的に確認してください。",
            ],
        }

    # ------------------------------------------------------------------
    # Asset write helpers
    # ------------------------------------------------------------------
    async def update_user_assets(self, user_id: str, assets: List[Dict[str, Any]]) -> bool:
        resolved_user_id, existing_rows = await self._resolve_user_id(user_id)
        if existing_rows:
            target_user_id = resolved_user_id
        else:
            target_user_id = user_id if user_id.startswith("user_") else f"user_{user_id}"

        async with get_db_session() as session:
            repo = UserRepository(session)
            try:
                for asset in assets:
                    asset_type = asset.get("asset_type") or asset.get("asset_key")
                    current_value = float(asset.get("current_value", 0.0))
                    target_allocation = float(asset.get("target_allocation", 0.0))
                    extra_data = asset.get("extra_data") or asset.get("details") or {}
                    if not asset_type:
                        continue
                    await repo.update_user_asset(
                        user_id=target_user_id,
                        asset_type=asset_type if isinstance(asset_type, str) else asset_type.value,
                        current_value=current_value,
                        target_allocation=target_allocation,
                        extra_data=extra_data,
                    )
            except Exception as exc:
                self._logger.error("Failed to update assets for %s: %s", user_id, exc)
                raise
        return True

    async def save_user_assets(self, user_id: str, assets_data: Dict[str, Any]) -> bool:
        """
        Accepts the dictionary format used by the REST layer and persists it.
        """
        normalized_assets: List[Dict[str, Any]] = []
        for key, payload in assets_data.items():
            if key == "summary":
                continue
            normalized_assets.append(
                {
                    "asset_type": key.upper(),
                    "current_value": payload.get("estimated_value", 0.0),
                    "target_allocation": payload.get("target_allocation", 0.0),
                    "extra_data": payload,
                }
            )
        return await self.update_user_assets(user_id, normalized_assets)

    async def add_user_asset(self, user_id: str, asset: Dict[str, Any]) -> bool:
        return await self.update_user_assets(user_id, [asset])

    async def delete_user_asset(self, user_id: str, asset_type: str) -> bool:
        """
        Soft delete: set value to zero.
        """
        asset = {"asset_type": asset_type, "current_value": 0.0, "target_allocation": 0.0}
        return await self.update_user_assets(user_id, [asset])

    # ------------------------------------------------------------------
    # Analytics helpers
    # ------------------------------------------------------------------
    async def get_market_valuation(self, category_id: int, condition: Optional[str] = None) -> Dict[str, Any]:
        """
        Produce a lightweight market valuation summary using transaction history.
        """
        async with get_db_session() as session:
            result = await session.execute(
                select(
                    func.count(Transaction.transaction_id),
                    func.avg(Transaction.price),
                    func.sum(Transaction.price),
                ).where(Transaction.category_id == category_id)
            )
            count, avg_price, total_value = result.one()

        return {
            "category_id": category_id,
            "transaction_count": int(count or 0),
            "average_price": float(avg_price or 0.0),
            "total_value": float(total_value or 0.0),
            "condition": condition or "standard",
        }

    async def get_user_activity_summary(self, user_id: str, days: int = 30) -> Dict[str, Any]:
        """
        Aggregate recent activity for dashboards.
        """
        since = datetime.utcnow() - timedelta(days=days)

        async with get_db_session() as session:
            transaction_result = await session.execute(
                select(func.count(Transaction.transaction_id), func.sum(Transaction.price))
                .where(
                    (Transaction.buyer_id == user_id) | (Transaction.seller_id == user_id),
                    Transaction.created >= since,
                )
            )
            txn_count, txn_total = transaction_result.one()

            balance_result = await session.execute(
                select(func.avg(DailyUserBalance.total_balance))
                .where(DailyUserBalance.user_id == user_id, DailyUserBalance.date >= since)
            )
            avg_balance = balance_result.scalar()

        return {
            "user_id": user_id,
            "period_days": days,
            "transaction_count": int(txn_count or 0),
            "transaction_volume": float(txn_total or 0.0),
            "average_balance": float(avg_balance or 0.0),
        }

    async def _mark_for_etl(self, doc_path: str, payload: Dict[str, Any]) -> None:
        """
        Placeholder for the original ETL hook. We simply log the intent.
        """
        self._logger.debug("Marking document for ETL sync: %s (payload keys=%s)", doc_path, list(payload.keys()))


# ----------------------------------------------------------------------
# Singleton factory used throughout the codebase
# ----------------------------------------------------------------------
_firestore_service_instance: Optional[FirestorePrimaryService] = None


def get_firestore_primary_service() -> FirestorePrimaryService:
    global _firestore_service_instance
    if _firestore_service_instance is None:
        _firestore_service_instance = FirestorePrimaryService()
    return _firestore_service_instance


__all__ = ["FirestorePrimaryService", "get_firestore_primary_service"]
