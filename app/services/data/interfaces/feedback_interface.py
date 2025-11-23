"""
feedbackdataサービスインターフェース

feedback recommendation関連 dataアクセス 抽象化
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional
from datetime import datetime

from app.models.recommendations import (
    AssetRecommendation, 
    RecommendationStatus, 
    RejectionReason,
    RecommendationFeedbackRequest
)


class FeedbackInterface(ABC):
    """
    feedbackdataサービス 抽象インターフェース
    
    userfeedback、recommendation履歴、および関連analysisdata 処理
    """
    
    @abstractmethod
    async def save_recommendation_feedback(self, feedback: RecommendationFeedbackRequest) -> bool:
        """
        recommendationfeedback save
        
        Args:
            feedback: feedbackリクエストオブジェクト
            
        Returns:
            save successしたかどうか
        """
        pass
    
    @abstractmethod
    async def get_user_feedback_history(self, user_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """
        userfeedback履歴 取得
        
        Args:
            user_id: userID
            limit: 返すcount 制限
            
        Returns:
            feedback履歴レコード list
        """
        pass
    
    @abstractmethod
    async def get_recommendation_performance(self, 
                                          recommendation_id: Optional[str] = None,
                                          agent_name: Optional[str] = None) -> Dict[str, Any]:
        """
        recommendationパフォーマンス統計 取得
        
        Args:
            recommendation_id: 特定 recommendationID、None すべて recommendation 意味する
            agent_name: 特定 agent名、None すべて agent 意味する
            
        Returns:
            recommendationパフォーマンス統計data
        """
        pass
    
    @abstractmethod
    async def save_recommendation_session(self, 
                                        user_id: str,
                                        session_data: Dict[str, Any]) -> str:
        """
        recommendationセッションdata save
        
        Args:
            user_id: userID
            session_data: セッションdata
            
        Returns:
            セッションID
        """
        pass
    
    @abstractmethod
    async def get_recommendation_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        recommendationセッションdata 取得
        
        Args:
            session_id: セッションID
            
        Returns:
            セッションdata、existsしない場合 None 返す
        """
        pass
    
    @abstractmethod
    async def get_user_recommendation_history(self, 
                                            user_id: str,
                                            start_date: Optional[datetime] = None,
                                            end_date: Optional[datetime] = None) -> List[AssetRecommendation]:
        """
        userrecommendation履歴 取得
        
        Args:
            user_id: userID
            start_date: 開始日
            end_date: 終了日
            
        Returns:
            recommendation履歴 list
        """
        pass
    
    @abstractmethod
    async def update_recommendation_status(self, 
                                         recommendation_id: str,
                                         status: RecommendationStatus,
                                         rejection_reason: Optional[RejectionReason] = None) -> bool:
        """
        recommendationステータス update
        
        Args:
            recommendation_id: recommendationID
            status: newステータス
            rejection_reason: 拒否理由（ステータス 拒否 場合）
            
        Returns:
            update successしたかどうか
        """
        pass
    
    @abstractmethod
    async def get_global_feedback_analytics(self, 
                                          time_range: str = '30d') -> Dict[str, Any]:
        """
        グローバルfeedbackanalysis 取得
        
        Args:
            time_range: 時間範囲 ('7d', '30d', '90d')
            
        Returns:
            グローバルfeedback統計およびanalysisdata
        """
        pass
    
    @abstractmethod
    async def get_rejection_reason_analytics(self, 
                                           agent_name: Optional[str] = None) -> Dict[str, Any]:
        """
        拒否理由analysis 取得
        
        Args:
            agent_name: 特定 agent、None すべて agent 意味する
            
        Returns:
            拒否理由 統計analysis
        """
        pass
