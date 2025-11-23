"""
コアanalysisサービス - 共有ビジネスロジック
FastAPI gRPCエンドPoints 共通してuseされる統一されたanalysisサービス provide
"""
from typing import Optional, Dict, Any, List
from datetime import datetime
import asyncio
import time

# プロジェクト コア依存関係
from app.agents.multi_agent_system import multi_agent_system
from app.services.firestore.firestore_primary_service import get_firestore_primary_service, FirestorePrimaryService
from app.services.bigquery.enhanced_client import get_enhanced_bigquery_client, EnhancedBigQueryClient
from app.models.assets import UserPortfolio, EnhancedUserPortfolio, UserProfile, TransactionBehavior, RiskProfile
from app.core.logging import logger


class AnalysisResult:
    """analysis結果dataクラス"""
    
    def __init__(
        self, 
        user_id: str, 
        analysis_summary: str,
        success: bool = True,
        error_message: Optional[str] = None,
        timestamp: Optional[int] = None
    ):
        self.user_id = user_id
        self.analysis_summary = analysis_summary
        self.success = success
        self.error_message = error_message
        self.timestamp = timestamp or int(time.time())
    
    def to_dict(self) -> Dict[str, Any]:
        """辞書形式 変換"""
        return {
            "user_id": self.user_id,
            "analysis_summary": self.analysis_summary,
            "success": self.success,
            "error_message": self.error_message,
            "timestamp": self.timestamp
        }


class CoreAnalysisService:
    """
    コアanalysisサービス - 統一されたビジネスロジック層
    
    こ サービス 、すべて analysis関連 コアビジネスロジック 含み、以下 エンドPoints useされます：
    - FastAPI RESTエンドPoints
    - gRPCサービスエンドPoints
    - in部サービス呼び出し
    """
    
    def __init__(self):
        """コアサービス 初期化"""
        self._firestore_service: Optional[FirestorePrimaryService] = None
        self._bigquery_client: Optional[EnhancedBigQueryClient] = None
        logger.info("CoreAnalysisService  初期化 完了しました")
    
    async def _get_firestore_service(self) -> FirestorePrimaryService:
        """Firestoreサービスインスタンス 取得（遅延読み込み）"""
        if self._firestore_service is None:
            self._firestore_service = get_firestore_primary_service()
            logger.debug("Firestoreサービスインスタンス 作成されました")
        return self._firestore_service
    
    async def _get_bigquery_client(self) -> EnhancedBigQueryClient:
        """BigQueryクライアントインスタンス 取得（遅延読み込み）"""
        if self._bigquery_client is None:
            self._bigquery_client = get_enhanced_bigquery_client()
            logger.debug("BigQueryクライアントインスタンス 作成されました")
        return self._bigquery_client
    
    # =============== コアanalysisメソッド ===============
    
    async def analyze_general_portfolio(
        self, 
        user_id: str, 
        allow_empty_portfolio: bool = False
    ) -> AnalysisResult:
        """
        user 総合portfolioanalysis 取得 - コアビジネスロジック
        
        Args:
            user_id: userID
            allow_empty_portfolio: 空 portfolio 許可するかどうか
            
        Returns:
            AnalysisResult: analysis結果
        """
        logger.info(f"総合analysis 開始: user_id={user_id}")
        
        try:
            # Firestoreサービス 取得
            firestore_service = await self._get_firestore_service()
            
            # Firestore from リアルタイム assetdata 取得
            portfolio = await firestore_service.get_user_portfolio(
                user_id, 
                allow_empty=allow_empty_portfolio, 
                raise_http_exception=False  # コアサービス HTTP例外 スローしない
            )
            
            if not portfolio and not allow_empty_portfolio:
                logger.warning(f"user {user_id}  portfolio 見つかりません")
                return AnalysisResult(
                    user_id=user_id,
                    analysis_summary="",
                    success=False,
                    error_message="指定されたuser portfolio 見つかりません"
                )
            
            # userfeedback履歴 取得（Firestore from ）
            feedback_history = await firestore_service.get_user_feedback_history(
                user_id, limit=10
            )
            
            # マルチagentシステム 呼び出してanalysis
            analysis_summary = await multi_agent_system.analyze_general_portfolio(
                portfolio, feedback_history
            )
            
            logger.info(f"総合analysis 完了: user_id={user_id}")
            
            return AnalysisResult(
                user_id=user_id,
                analysis_summary=analysis_summary,
                success=True
            )
            
        except Exception as e:
            logger.error(f"総合analysis failed: user_id={user_id}, error={e}")
            return AnalysisResult(
                user_id=user_id,
                analysis_summary="",
                success=False,
                error_message=str(e)
            )
    
    async def get_enhanced_user_analysis(
        self, 
        user_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        user enhanceanalysisレポート 取得 - BigQuerydata 基づく
        
        Args:
            user_id: userID
            
        Returns:
            Dict: enhanceanalysis結果、failedした場合 None 返す
        """
        try:
            logger.info(f"🎯 enhanceuseranalysis 開始: user_id={user_id}")
            
            # BigQueryクライアント 取得
            bq_client = await self._get_bigquery_client()
            
            # enhanceportfolio 取得
            enhanced_portfolio = await bq_client.get_enhanced_user_portfolio(user_id)
            
            if not enhanced_portfolio:
                logger.warning(f"user {user_id}  enhancedata 見つかりません")
                return None
            
            # レスポンスdata build
            response = {
                "user_id": user_id,
                "analysis_timestamp": datetime.now().isoformat(),
                "data_completeness": {
                    "basic_assets": True,
                    "user_profile": enhanced_portfolio.user_profile is not None,
                    "transaction_behavior": enhanced_portfolio.transaction_behavior is not None,
                    "risk_assessment": enhanced_portfolio.risk_profile is not None,
                    "personalized_insights": enhanced_portfolio.personalized_insights is not None
                },
                
                # 基本asset情報
                "asset_summary": {
                    "total_estimated_value": enhanced_portfolio.total_estimated_value,
                    "asset_count": len(enhanced_portfolio.assets),
                    "last_updated": enhanced_portfolio.last_updated.isoformat() if enhanced_portfolio.last_updated else None
                },
                
                # userプロファイルインサイト
                "user_profile_insights": self._build_profile_insights(enhanced_portfolio.user_profile),
                
                # 取引行動インサイト
                "transaction_insights": self._build_transaction_insights(enhanced_portfolio.transaction_behavior),
                
                # リスク評価結果
                "risk_assessment": self._build_risk_assessment(enhanced_portfolio.risk_profile),
                
                # パーソナライズされたrecommendation
                "personalized_recommendations": self._build_personalized_recommendations(enhanced_portfolio)
            }
            
            logger.info(f"✅ enhanceuseranalysis 完了: user_id={user_id}")
            return response
            
        except Exception as e:
            logger.error(f"❌ enhanceuseranalysis failed: user_id={user_id}, error={e}")
            return None
    
    async def get_user_profile_analysis(
        self, 
        user_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        userプロファイルanalysis 取得
        
        Args:
            user_id: userID
            
        Returns:
            Dict: userプロファイルanalysis結果、failedした場合 None 返す
        """
        try:
            logger.info(f"userプロファイルanalysis 取得: {user_id}")
            
            # BigQueryクライアント 取得
            bq_client = await self._get_bigquery_client()
            
            # userプロファイル 取得
            user_profile = await bq_client.get_user_profile(user_id)
            
            if not user_profile:
                logger.warning(f"user {user_id}  プロファイルdata 見つかりません")
                return None
            
            return {
                "user_id": user_id,
                "profile_data": user_profile.dict(),
                "analysis_summary": {
                    "account_maturity": self._calculate_account_maturity(user_profile.registration_date),
                    "demographic_segment": self._get_demographic_segment(user_profile),
                    "engagement_level": self._get_engagement_level(user_profile)
                }
            }
            
        except Exception as e:
            logger.error(f"userプロファイル 取得 failed: {e}")
            return None
    
    async def get_transaction_behavior_analysis(
        self, 
        user_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        取引行動analysis 取得
        
        Args:
            user_id: userID
            
        Returns:
            Dict: 取引行動analysis結果、failedした場合 None 返す
        """
        try:
            logger.info(f"取引行動 analysis: {user_id}")
            
            # BigQueryクライアント 取得
            bq_client = await self._get_bigquery_client()
            
            # 取引行動data 取得
            behavior = await bq_client.get_user_transaction_behavior(user_id)
            
            if not behavior:
                logger.warning(f"user {user_id}  取引記録 not available")
                return None
            
            return {
                "user_id": user_id,
                "behavior_data": behavior.dict(),
                "behavior_classification": {
                    "user_type": self._classify_user_type(behavior),
                    "activity_level": self._classify_activity_level(behavior),
                    "spending_pattern": self._classify_spending_pattern(behavior),
                    "reliability_tier": self._classify_reliability(behavior)
                },
                "comparison_metrics": {
                    "vs_platform_average": self._generate_platform_comparison(behavior)
                }
            }
            
        except Exception as e:
            logger.error(f"取引行動analysis failed: {e}")
            return None
    
    # =============== ヘルパーメソッド ===============
    
    def _build_profile_insights(
        self, 
        user_profile: Optional[UserProfile]
    ) -> Dict[str, Any]:
        """userプロファイルインサイト build"""
        if not user_profile:
            return {}
        
        profile_insights = {
            "demographic_profile": {
                "age_group": user_profile.age_group,
                "gender": user_profile.gender,
                "occupation": user_profile.occupation,
                "prefecture": user_profile.prefecture,
                "ekyc_status": user_profile.ekyc_status
            }
        }
        
        if user_profile.registration_date:
            profile_insights["registration_info"] = {
                "registration_date": user_profile.registration_date.isoformat(),
                "account_age_days": (datetime.now() - user_profile.registration_date).days,
                "nickname": user_profile.basic_info.get("nickname"),
                "account_status": user_profile.basic_info.get("status")
            }
        
        return profile_insights
    
    def _build_transaction_insights(
        self, 
        transaction_behavior: Optional[TransactionBehavior]
    ) -> Dict[str, Any]:
        """取引行動インサイト build"""
        if not transaction_behavior:
            return {}
        
        behavior = transaction_behavior
        return {
            "activity_summary": {
                "total_transactions": behavior.total_transactions,
                "total_transaction_value": behavior.total_transaction_value,
                "average_transaction_amount": round(behavior.avg_transaction_amount, 2),
                "transaction_frequency_monthly": round(behavior.transaction_frequency, 1),
                "last_transaction_date": behavior.last_transaction_date.isoformat() if behavior.last_transaction_date else None
            },
            "role_analysis": {
                "as_buyer_transactions": behavior.as_buyer_count,
                "as_seller_transactions": behavior.as_seller_count,
                "buyer_seller_ratio": round(behavior.buyer_seller_ratio, 2),
                "preferred_role": "buyer" if behavior.buyer_seller_ratio > 1.5 else "seller" if behavior.buyer_seller_ratio < 0.67 else "balanced"
            },
            "payment_preferences": {
                "preferred_payment_methods": behavior.preferred_payment_methods,
                "payment_distribution": behavior.payment_method_distribution,
                "point_usage_rate": round(behavior.point_usage_rate * 100, 1),
                "sales_fund_usage_rate": round(behavior.sales_fund_usage_rate * 100, 1)
            },
            "shopping_patterns": {
                "preferred_categories": behavior.preferred_categories[:3],
                "price_preferences": behavior.price_range_preference,
                "transaction_volatility": round(behavior.transaction_volatility, 0)
            },
            "reliability_metrics": {
                "completion_rate": round(behavior.completed_transaction_rate * 100, 1),
                "cancellation_rate": round(behavior.cancellation_rate * 100, 1),
                "reliability_score": "excellent" if behavior.completed_transaction_rate > 0.9 else "good" if behavior.completed_transaction_rate > 0.8 else "needs_improvement"
            }
        }
    
    def _build_risk_assessment(
        self, 
        risk_profile: Optional[RiskProfile]
    ) -> Dict[str, Any]:
        """リスク評価 build"""
        if not risk_profile:
            return {}
        
        risk = risk_profile
        return {
            "overall_risk": {
                "risk_level": risk.risk_level,
                "risk_score": round(risk.risk_score, 1),
                "risk_interpretation": self._get_risk_interpretation(risk.risk_level)
            },
            "behavioral_analysis": {
                "liquidity_preference": risk.liquidity_preference,
                "investment_tendency": risk.investment_tendency,
                "financial_stability": risk.financial_stability,
                "liquidity_score": round(risk.liquidity_score * 100, 1),
                "investment_score": round(risk.investment_score * 100, 1),
                "stability_score": round(risk.stability_score * 100, 1)
            },
            "risk_factors": {
                "age_risk_factor": round(risk.age_risk_factor * 100, 1),
                "occupation_risk_factor": round(risk.occupation_risk_factor * 100, 1),
                "transaction_pattern_risk": round(risk.transaction_pattern_risk_factor * 100, 1)
            },
            "asset_allocation_recommendation": risk.recommended_asset_allocation,
            "suitable_products": risk.suitable_financial_products,
            "risk_warnings": risk.risk_warnings
        }
    
    def _build_personalized_recommendations(
        self, 
        enhanced_portfolio: EnhancedUserPortfolio
    ) -> Dict[str, Any]:
        """パーソナライズされたrecommendation build"""
        if not enhanced_portfolio.personalized_insights:
            return {}
        
        insights = enhanced_portfolio.personalized_insights
        return {
            "behavioral_insights": insights.behavioral_insights,
            "risk_insights": insights.risk_insights,
            "opportunity_insights": insights.opportunity_insights,
            "warning_insights": insights.warning_insights,
            "recommendation_weights": insights.recommendation_weights,
            "priority_actions": self._generate_priority_actions(enhanced_portfolio),
            "next_steps": self._generate_next_steps(enhanced_portfolio)
        }
    
    # =============== 分類 評価メソッド ===============
    
    def _get_risk_interpretation(self, risk_level: str) -> str:
        """リスクレベル 解釈"""
        interpretations = {
            "conservative": "保守型 - 安定した収益 好み、リスク許容度 低い",
            "moderate": "バランス型 - 適度な収益 追求し、中程度 リスク 許容 きる",
            "aggressive": "積極型 - 高い収益 追求し、高いリスク許容度 持つ"
        }
        return interpretations.get(risk_level, "不明なリスクタイプ")
    
    def _generate_priority_actions(self, portfolio: EnhancedUserPortfolio) -> List[str]:
        """優firstアクション 提案 generate"""
        actions = []
        
        if portfolio.risk_profile and portfolio.transaction_behavior:
            # analysis結果 基づく具体 な提案 generate
            if portfolio.transaction_behavior.point_usage_rate > 0.8:
                actions.append("緊急資金 して一部 Points 保持するこ  検討")
            
            if portfolio.transaction_behavior.cancellation_rate > 0.15:
                actions.append("取引決定プロセス 改善し、キャンセル率 低下させる")
            
            if portfolio.risk_profile.risk_level == "aggressive" and portfolio.transaction_behavior.as_seller_count > 0:
                actions.append("商品販売規模 拡大し、受動 収入 increase")
            
            if portfolio.risk_profile.liquidity_preference == "high":
                actions.append("Points 資金 流動性配分 最適化する")
        
        return actions or ["良好なasset管理習慣 維持し続ける"]
    
    def _generate_next_steps(self, portfolio: EnhancedUserPortfolio) -> List[str]:
        """次 ステップ 提案 generate"""
        steps = []
        
        if portfolio.user_profile and portfolio.user_profile.age_group:
            if portfolio.user_profile.age_group in ["young_adult", "early_career"]:
                steps.append("長期 な投資計画 立て、時間 利点 utilizeする")
            elif portfolio.user_profile.age_group == "mid_career":
                steps.append("asset配分 enhanceし、将来 備える")
        
        if portfolio.transaction_behavior:
            if portfolio.transaction_behavior.total_transactions < 10:
                steps.append("プラットフォーム  取引経験 増やし、信用記録 buildする")
            else:
                steps.append("取引経験 based on、さらなるasset運用 選択肢 探る")
        
        return steps or ["定期  asset配分戦略 見直し、adjustする"]
    
    def _calculate_account_maturity(self, registration_date: Optional[datetime]) -> str:
        """アカウント 成熟度 計算"""
        if not registration_date:
            return "unknown"
        
        days = (datetime.now() - registration_date).days
        
        if days < 30:
            return "new_user"
        elif days < 180:
            return "developing_user"
        elif days < 365:
            return "established_user"
        else:
            return "mature_user"
    
    def _get_demographic_segment(self, profile: UserProfile) -> str:
        """人口統計学 セグメント 取得"""
        if not profile.age_group or not profile.occupation:
            return "unknown_segment"
        
        # year齢層 職業 基づくセグメント
        if profile.age_group == "young_adult" and profile.occupation in ["学生", "アルバイト"]:
            return "young_learners"
        elif profile.age_group in ["early_career", "mid_career"] and profile.occupation == "会社員":
            return "working_professionals"
        elif profile.occupation == "公務員":
            return "stable_income_group"
        elif profile.occupation == "自営業":
            return "entrepreneurs"
        else:
            return "general_users"
    
    def _get_engagement_level(self, profile: UserProfile) -> str:
        """userエンゲージメントレベル 取得"""
        if profile.basic_info.get("description"):
            return "high_engagement"
        elif profile.basic_info.get("nickname"):
            return "medium_engagement"
        else:
            return "low_engagement"
    
    def _classify_user_type(self, behavior: TransactionBehavior) -> str:
        """userタイプ 分類"""
        if behavior.buyer_seller_ratio > 2:
            return "primary_buyer"
        elif behavior.buyer_seller_ratio < 0.5:
            return "primary_seller"
        elif behavior.total_transactions > 15:
            return "active_trader"
        else:
            return "casual_user"
    
    def _classify_activity_level(self, behavior: TransactionBehavior) -> str:
        """活動レベル 分類"""
        if behavior.transaction_frequency > 10:
            return "highly_active"
        elif behavior.transaction_frequency > 5:
            return "moderately_active"
        elif behavior.transaction_frequency > 2:
            return "occasionally_active"
        else:
            return "low_activity"
    
    def _classify_spending_pattern(self, behavior: TransactionBehavior) -> str:
        """消費パターン 分類"""
        if behavior.avg_transaction_amount > 5000:
            return "high_value_spender"
        elif behavior.avg_transaction_amount > 2000:
            return "medium_value_spender"
        else:
            return "budget_conscious"
    
    def _classify_reliability(self, behavior: TransactionBehavior) -> str:
        """信頼性 分類"""
        if behavior.completed_transaction_rate > 0.95 and behavior.cancellation_rate < 0.05:
            return "highly_reliable"
        elif behavior.completed_transaction_rate > 0.85 and behavior.cancellation_rate < 0.15:
            return "reliable"
        elif behavior.completed_transaction_rate > 0.7:
            return "moderately_reliable"
        else:
            return "needs_improvement"
    
    def _generate_platform_comparison(self, behavior: TransactionBehavior) -> Dict[str, str]:
        """プラットフォーム比較指標 generate"""
        return {
            "transaction_frequency": "above_average" if behavior.transaction_frequency > 6 else "below_average",
            "completion_rate": "excellent" if behavior.completed_transaction_rate > 0.9 else "good" if behavior.completed_transaction_rate > 0.8 else "needs_improvement",
            "avg_transaction_value": "high" if behavior.avg_transaction_amount > 3000 else "medium" if behavior.avg_transaction_amount > 1500 else "low"
        }


# =============== シングルトンインスタンス ===============

_core_analysis_service: Optional[CoreAnalysisService] = None


def get_core_analysis_service() -> CoreAnalysisService:
    """
    コアanalysisサービス シングルトンインスタンス 取得
    
    Returns:
        CoreAnalysisService: コアanalysisサービスインスタンス
    """
    global _core_analysis_service
    if _core_analysis_service is None:
        _core_analysis_service = CoreAnalysisService()
        logger.info("コアanalysisサービス シングルトンインスタンス 作成されました")
    return _core_analysis_service
