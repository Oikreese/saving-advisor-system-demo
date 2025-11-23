"""
模擬feedbackdataサービス 実装

既存 Firestoreストレージ BigQueryanalysis 基づく実装
"""

from typing import Dict, List, Any, Optional
from datetime import datetime
import logging
import uuid

from app.services.data.interfaces.feedback_interface import FeedbackInterface
from app.models.recommendations import (
    AssetRecommendation, 
    RecommendationStatus, 
    RejectionReason,
    RecommendationFeedbackRequest
)
from app.services.firestore.firestore_primary_service import FirestorePrimaryService
from app.services.bigquery.analytics_engine import BigQueryAnalyticsEngine


logger = logging.getLogger(__name__)


class MockFeedbackDataService(FeedbackInterface):
    """
    模擬feedbackdataサービス
    
    現在 実装：既存 FirestoreおよびBigQueryサービス use
    将来 移行：Mercariメインアプリケーション feedbackAPI呼び出し 置き換え
    """
    
    def __init__(self, 
                 firestore_service: Optional[FirestorePrimaryService] = None,
                 analytics_engine: Optional[BigQueryAnalyticsEngine] = None):
        self.firestore_service = firestore_service or FirestorePrimaryService()
        self.analytics_engine = analytics_engine or BigQueryAnalyticsEngine()
        logger.info("MockFeedbackDataService initialized - using Firestore/BigQuery backend")
    
    async def save_recommendation_feedback(self, feedback: RecommendationFeedbackRequest) -> bool:
        """recommendationfeedback Firestore save"""
        try:
            # ストレージ形式 変換
            feedback_data = {
                'user_id': feedback.user_id,
                'recommendation_id': feedback.recommendation_id,
                'status': feedback.status.value,
                'rejection_reason': feedback.rejection_reason.value if feedback.rejection_reason else None,
                'rejection_detail': feedback.rejection_detail,
                'created_at': datetime.now().isoformat(),
                'agent_name': getattr(feedback, 'agent_name', None),
                'feedback_score': getattr(feedback, 'feedback_score', None)
            }
            
            # Firestore save
            success = await self.firestore_service.save_recommendation_feedback(
                feedback.user_id, 
                feedback.recommendation_id, 
                feedback_data
            )
            
            if success:
                logger.info(f"Successfully saved feedback for recommendation {feedback.recommendation_id}")
            return success
            
        except Exception as e:
            logger.error(f"Error saving recommendation feedback: {e}")
            return False
    
    async def get_user_feedback_history(self, user_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """user feedback履歴 取得"""
        try:
            feedback_history = await self.firestore_service.get_user_feedback_history(
                user_id, limit=limit
            )
            return feedback_history or []
        except Exception as e:
            logger.error(f"Error getting user feedback history for {user_id}: {e}")
            return []
    
    async def get_recommendation_performance(self, 
                                          recommendation_id: Optional[str] = None,
                                          agent_name: Optional[str] = None) -> Dict[str, Any]:
        """recommendationパフォーマンス統計 取得"""
        try:
            # BigQueryanalysisエンジン useしてrecommendationパフォーマンスdata 取得
            performance_data = await self.analytics_engine.analyze_recommendation_performance()
            
            if recommendation_id:
                # 特定 recommendation data フィルタリング
                return self._filter_performance_by_recommendation(performance_data, recommendation_id)
            elif agent_name:
                # 特定 agent data フィルタリング
                return self._filter_performance_by_agent(performance_data, agent_name)
            else:
                # すべて パフォーマンスdata 返す
                return performance_data
                
        except Exception as e:
            logger.error(f"Error getting recommendation performance: {e}")
            return {}
    
    async def save_recommendation_session(self, 
                                        user_id: str,
                                        session_data: Dict[str, Any]) -> str:
        """recommendationセッションdata save"""
        try:
            session_id = str(uuid.uuid4())
            session_record = {
                'session_id': session_id,
                'user_id': user_id,
                'created_at': datetime.now().isoformat(),
                'session_data': session_data
            }
            
            success = await self.firestore_service.save_recommendation_session(
                user_id, session_id, session_record
            )
            
            if success:
                logger.info(f"Successfully saved recommendation session {session_id}")
                return session_id
            else:
                raise Exception("セッション Firestoreへ save failed")
                
        except Exception as e:
            logger.error(f"Error saving recommendation session: {e}")
            return ""
    
    async def get_recommendation_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """recommendationセッションdata 取得"""
        try:
            session_data = await self.firestore_service.get_recommendation_session(session_id)
            return session_data
        except Exception as e:
            logger.error(f"Error getting recommendation session {session_id}: {e}")
            return None
    
    async def get_user_recommendation_history(self, 
                                            user_id: str,
                                            start_date: Optional[datetime] = None,
                                            end_date: Optional[datetime] = None) -> List[AssetRecommendation]:
        """user recommendation履歴 取得"""
        try:
            history_data = await self.firestore_service.get_user_recommendation_history(
                user_id, start_date, end_date
            )
            
            # AssetRecommendationオブジェクト 変換
            recommendations = []
            for item in history_data:
                try:
                    recommendation = AssetRecommendation(**item)
                    recommendations.append(recommendation)
                except Exception as e:
                    logger.warning(f"Failed to parse recommendation item: {e}")
                    continue
                    
            return recommendations
            
        except Exception as e:
            logger.error(f"Error getting user recommendation history for {user_id}: {e}")
            return []
    
    async def update_recommendation_status(self, 
                                         recommendation_id: str,
                                         status: RecommendationStatus,
                                         rejection_reason: Optional[RejectionReason] = None) -> bool:
        """recommendationステータス update"""
        try:
            update_data = {
                'status': status.value,
                'updated_at': datetime.now().isoformat()
            }
            
            if rejection_reason:
                update_data['rejection_reason'] = rejection_reason.value
            
            success = await self.firestore_service.update_recommendation_status(
                recommendation_id, update_data
            )
            
            if success:
                logger.info(f"Successfully updated recommendation {recommendation_id} status to {status.value}")
                
            return success
            
        except Exception as e:
            logger.error(f"Error updating recommendation status: {e}")
            return False
    
    async def get_global_feedback_analytics(self, time_range: str = '30d') -> Dict[str, Any]:
        """グローバルfeedbackanalysis 取得"""
        try:
            # 時間範囲 変換
            days_map = {'7d': 7, '30d': 30, '90d': 90}
            days = days_map.get(time_range, 30)
            
            analytics_data = await self.analytics_engine.analyze_global_feedback_trends(days=days)
            return analytics_data
            
        except Exception as e:
            logger.error(f"Error getting global feedback analytics: {e}")
            return {}
    
    async def get_rejection_reason_analytics(self, 
                                           agent_name: Optional[str] = None) -> Dict[str, Any]:
        """拒否理由analysis 取得"""
        try:
            rejection_analytics = await self.analytics_engine.analyze_rejection_reasons()
            
            if agent_name:
                # 特定 agent data フィルタリング
                return self._filter_rejection_by_agent(rejection_analytics, agent_name)
            else:
                return rejection_analytics
                
        except Exception as e:
            logger.error(f"Error getting rejection reason analytics: {e}")
            return {}
    
    def _filter_performance_by_recommendation(self, 
                                            performance_data: Dict[str, Any], 
                                            recommendation_id: str) -> Dict[str, Any]:
        """recommendationID based onパフォーマンスdata フィルタリング"""
        try:
            recommendations = performance_data.get('recommendations', {})
            if recommendation_id in recommendations:
                return {
                    'recommendation_id': recommendation_id,
                    'performance': recommendations[recommendation_id],
                    'timestamp': performance_data.get('timestamp')
                }
            return {}
        except Exception as e:
            logger.error(f"Error filtering performance by recommendation {recommendation_id}: {e}")
            return {}
    
    def _filter_performance_by_agent(self, 
                                   performance_data: Dict[str, Any], 
                                   agent_name: str) -> Dict[str, Any]:
        """agent名 based onパフォーマンスdata フィルタリング"""
        try:
            agents = performance_data.get('agents', {})
            if agent_name in agents:
                return {
                    'agent_name': agent_name,
                    'performance': agents[agent_name],
                    'timestamp': performance_data.get('timestamp')
                }
            return {}
        except Exception as e:
            logger.error(f"Error filtering performance by agent {agent_name}: {e}")
            return {}
    
    def _filter_rejection_by_agent(self, 
                                 rejection_data: Dict[str, Any], 
                                 agent_name: str) -> Dict[str, Any]:
        """agent名 based on拒否理由data フィルタリング"""
        try:
            agents_rejection = rejection_data.get('by_agent', {})
            if agent_name in agents_rejection:
                return {
                    'agent_name': agent_name,
                    'rejection_analysis': agents_rejection[agent_name],
                    'timestamp': rejection_data.get('timestamp')
                }
            return {}
        except Exception as e:
            logger.error(f"Error filtering rejection by agent {agent_name}: {e}")
            return {}


# シングルトンファクトリ関数
_mock_feedback_service_instance = None

def get_mock_feedback_service() -> MockFeedbackDataService:
    """MockFeedbackDataService シングルトンインスタンス 取得"""
    global _mock_feedback_service_instance
    if _mock_feedback_service_instance is None:
        _mock_feedback_service_instance = MockFeedbackDataService()
    return _mock_feedback_service_instance
