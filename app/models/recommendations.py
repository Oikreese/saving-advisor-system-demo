from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Any
from datetime import datetime
from app.models.assets import AssetType, RiskLevel
from enum import Enum

class RecommendationStatus(str, Enum):
    PENDING = "pending"
    ACCEPTED = "accepted" 
    REJECTED = "rejected"
    IMPLEMENTED = "implemented"

class RejectionReason(str, Enum):
    TOO_COMPLEX = "提案 複雑・面倒"
    HIGH_RISK = "リスク 高い"
    NOT_INTERESTED = "興味 ない"
    OTHER = "そ 他"

class ActionType(str, Enum):
    INCREASE_SAVINGS = "increase_savings"
    INVEST_ASSETS = "invest_assets"
    SELL_ITEMS = "sell_items"
    PARTICIPATE_CAMPAIGNS = "participate_campaigns"
    CONVERT_POINTS = "convert_points"
    MANAGE_PORTFOLIO = "manage_portfolio"

class RecommendationDetail(BaseModel):
    title: str = Field(..., description="推奨タイトル")
    description: str = Field(..., description="具体的な推奨in容")
    potential_gain: float = Field(..., description="期待される潜在的な利益（円単位）")

class AssetRecommendation(BaseModel):
    recommendation_id: str = Field(..., description="推奨ID")
    user_id: str = Field(..., description="userID")
    asset_type: AssetType = Field(..., description="対象assetタイプ")
    title: str = Field(..., description="推奨タイトル")
    description: str = Field(..., description="推奨in容詳細")
    action_type: ActionType = Field(..., description="アクションタイプ")
    expected_impact: float = Field(..., description="期待される効果 (increase額)")
    confidence_score: float = Field(..., ge=0, le=1, description="信頼度スコア")
    risk_level: RiskLevel = Field(..., description="リスクレベル")
    implementation_steps: List[str] = Field(default=[], description="実装手順")
    status: RecommendationStatus = Field(default=RecommendationStatus.PENDING, description="ステータス")
    rejection_reason: Optional[RejectionReason] = Field(default=None, description="拒绝理由")
    rejection_feedback: Optional[str] = Field(default=None, description="user自定义拒绝feedback")
    created_at: datetime = Field(default_factory=datetime.now, description="作成日時")
    expires_at: Optional[datetime] = Field(default=None, description="有効期限")

class RecommendationFeedbackRequest(BaseModel):
    recommendation_id: str
    user_id: str
    status: RecommendationStatus
    rejection_reason: Optional[str] = None
    rejection_feedback: Optional[str] = None

class RegenerationRequest(BaseModel):
    user_id: str
    recommendation_id: str
    agent_name: str
    rejection_reason: str
    rejection_detail: Optional[str] = None

class RecommendationAcceptanceRequest(BaseModel):
    user_id: str
    recommendation_id: str
    accepted_at: datetime = Field(default_factory=datetime.now)

class FinalizeSessionRequest(BaseModel):
    user_id: str
    feedback: Dict[str, Any]
    session_type: str
    input_data: Dict[str, Any]
    ai_response: List[Dict[str, Any]]
    processing_time_ms: int

class ComprehensiveRecommendation(BaseModel):
    user_id: str = Field(..., description="userID")
    asset_recommendations: List[AssetRecommendation] = Field(..., description="各asset 推奨list")
    accepted_recommendations: List[str] = Field(default=[], description="受諾された推奨ID")
    total_expected_growth: float = Field(..., description="総期待成長額")
    overall_risk_level: RiskLevel = Field(..., description="全体リスクレベル")
    implementation_priority: List[str] = Field(default=[], description="実装優先順位")
    initial_assets: float = Field(..., description="初期総asset")
    predicted_assets: float = Field(..., description="予測総asset")
    comprehensive_summary: str = Field(..., description="総合的な概要")
    created_at: datetime = Field(default_factory=datetime.now, description="作成日時")

class UserTask(BaseModel):
    task_id: str = Field(..., description="タスクID")
    user_id: str = Field(..., description="userID")
    title: str = Field(..., description="タスクタイトル")
    description: str = Field(..., description="タスク詳細")
    related_asset_type: Optional[AssetType] = Field(default=None, description="関連assetタイプ")
    related_recommendation_id: Optional[str] = Field(default=None, description="関連推奨ID")
    due_date: Optional[datetime] = Field(default=None, description="期限")
    is_completed: bool = Field(default=False, description="完了フラグ")
    completion_reward: Optional[float] = Field(default=None, description="完了報酬")
    created_at: datetime = Field(default_factory=datetime.now, description="作成日時")
    completed_at: Optional[datetime] = Field(default=None, description="完了日時")

class MonthlyTaskList(BaseModel):
    user_id: str = Field(..., description="userID")
    month: str = Field(..., description="対象month (YYYY-MM)")
    tasks: List[UserTask] = Field(..., description="タスクlist")
    total_tasks: int = Field(..., description="総タスク数")
    completed_tasks: int = Field(default=0, description="完了タスク数")
    estimated_total_reward: float = Field(..., description="推定総報酬")
    predicted_total_benefit: Optional[str] = Field(default=None, description="LLM よって予測された総利益")
    created_at: datetime = Field(default_factory=datetime.now, description="作成日時")

# LLM Agent Response Models
class AgentAnalysis(BaseModel):
    agent_name: str = Field(..., description="agent名")
    asset_type: AssetType = Field(..., description="analysis対象 assetタイプ")
    findings: str = Field(..., description="発見事項")
    recommendations: List[RecommendationDetail] = Field(..., description="recommendationslist")
    reasoning: Optional[str] = Field(default=None, description="推論過程")
    generated_at: datetime = Field(default_factory=datetime.now, description="generate日時")

class MultiAgentResponse(BaseModel):
    user_id: str = Field(..., description="userID")
    analyses: List[AgentAnalysis] = Field(..., description="各agent analysis結果")
    consensus_recommendations: List[str] = Field(..., description="合意されたrecommendations")
    conflicting_opinions: Optional[List[str]] = Field(default=[], description="意見 相違点")
    overall_assessment: str = Field(..., description="全体評価")
    generated_at: datetime = Field(default_factory=datetime.now, description="generate日時")