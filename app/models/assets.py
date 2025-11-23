from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Any
from datetime import datetime
from enum import Enum

class AssetType(str, Enum):
    POINTS = "ポイント"
    EARNINGS = "売上金・給与・報酬"
    ITEMS = "モノ"
    GIGA = "ギガ"
    STABLECOIN = "ステーブルコイン"

class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"

class UserAsset(BaseModel):
    user_id: str = Field(..., description="userID")
    asset_type: AssetType = Field(..., description="assetタイプ")
    current_value: float = Field(..., ge=0, description="現在価値")
    currency: str = Field(default="JPY", description="通貨単位")
    last_updated: datetime = Field(default_factory=datetime.now, description="最終update日時")
    metadata: Optional[Dict] = Field(default={}, description="appendメタdata")

class UserPortfolio(BaseModel):
    user_id: str = Field(..., description="userID")
    total_assets: float = Field(..., ge=0, description="総asset額")
    assets: List[UserAsset] = Field(..., description="assetlist")
    risk_profile: RiskLevel = Field(default=RiskLevel.MEDIUM, description="リスクプロファイル")
    last_analyzed: Optional[datetime] = Field(default=None, description="最終analysis日時")

    @classmethod
    def from_bq_dict(cls, user_id: str, bq_data: Dict[str, Any]) -> "UserPortfolio":
        assets_list = []
        total_value = 0
        asset_type_map = {
            'points': AssetType.POINTS,
            'earnings': AssetType.EARNINGS,
            'items': AssetType.ITEMS,
            'giga': AssetType.GIGA,
            'stablecoin': AssetType.STABLECOIN,
        }

        for key, asset_type in asset_type_map.items():
            asset_data = bq_data.get(key, {})
            value = asset_data.get('estimated_value', 0)
            assets_list.append(UserAsset(
                user_id=user_id,
                asset_type=asset_type,
                current_value=value,
                metadata=asset_data
            ))
            total_value += value

        return cls(
            user_id=user_id,
            total_assets=total_value,
            assets=assets_list
        )

class AssetAnalysis(BaseModel):
    user_id: str = Field(..., description="userID")
    asset_type: AssetType = Field(..., description="analysis対象assetタイプ")
    current_status: str = Field(..., description="現状analysis")
    growth_potential: float = Field(..., ge=0, le=1, description="成長ポテンシャル (0-1)")
    risk_assessment: RiskLevel = Field(..., description="リスク評価")
    recommendations: List[str] = Field(default=[], description="recommendations")
    analyzed_at: datetime = Field(default_factory=datetime.now, description="analysisexecute日時")

class AssetVisualization(BaseModel):
    user_id: str = Field(..., description="userID")
    chart_type: str = Field(default="pie", description="チャートタイプ")
    chart_data: Dict = Field(..., description="チャートdata")
    total_value: float = Field(..., ge=0, description="総価値")
    asset_breakdown: Dict[str, float] = Field(..., description="assetin訳")
    generated_at: datetime = Field(default_factory=datetime.now, description="generate日時")




# ============== enhanceanalysisdatamodel ==============

class UserProfile(BaseModel):
    """user完整画像data"""
    user_id: str
    basic_info: Dict[str, Any] = Field(default_factory=dict)  # 来自userstable
    demographic_info: Dict[str, Any] = Field(default_factory=dict)  # 来自v2_customertable
    ekyc_status: Optional[str] = None
    registration_date: Optional[datetime] = None
    
    # decrypt后的个人info
    gender: Optional[str] = None
    occupation: Optional[str] = None
    prefecture: Optional[str] = None
    birth_year: Optional[int] = None
    age_group: Optional[str] = None  # 计算得出的year龄段


class TransactionBehavior(BaseModel):
    """usertransactionbehavioranalysis"""
    user_id: str
    # transactionstatistics
    total_transactions: int = 0
    total_transaction_value: float = 0.0
    avg_transaction_amount: float = 0.0
    transaction_volatility: float = 0.0  # transactionamount标准差
    
    # transaction角色analysis
    as_buyer_count: int = 0
    as_seller_count: int = 0
    buyer_seller_ratio: float = 0.0
    
    # 支付偏好
    preferred_payment_methods: List[str] = Field(default_factory=list)
    payment_method_distribution: Dict[str, float] = Field(default_factory=dict)
    
    # 商品偏好
    preferred_categories: List[Dict[str, Any]] = Field(default_factory=list)
    price_range_preference: Dict[str, float] = Field(default_factory=dict)
    
    # timebehavior
    transaction_frequency: float = 0.0  # 每month平均transaction次数
    most_active_hours: List[int] = Field(default_factory=list)
    last_transaction_date: Optional[datetime] = None
    
    # 点数和资金use习惯
    point_usage_rate: float = 0.0  # 积分use比例
    sales_fund_usage_rate: float = 0.0  # 销售资金use比例
    
    # transactionsuccess率
    completed_transaction_rate: float = 0.0
    cancellation_rate: float = 0.0


class RiskProfile(BaseModel):
    """user风险画像"""
    user_id: str
    # 风险等级
    risk_level: str = "unknown"  # conservative, moderate, aggressive
    risk_score: float = 0.0  # 0-100的风险评分
    
    # 流动性偏好
    liquidity_preference: str = "unknown"  # high, medium, low
    liquidity_score: float = 0.0  # 0-1，越高越偏好流动性
    
    # 投资倾向
    investment_tendency: str = "unknown"  # spender, saver, investor
    investment_score: float = 0.0  # 0-1，越高越倾向投资
    
    # 稳定性metric
    financial_stability: str = "unknown"  # stable, volatile, unpredictable
    stability_score: float = 0.0  # 0-1，越高越稳定
    
    # 基于人口statistics学的风险因子
    age_risk_factor: float = 0.0
    occupation_risk_factor: float = 0.0
    transaction_pattern_risk_factor: float = 0.0
    
    # recommendation建议
    recommended_asset_allocation: Dict[str, float] = Field(default_factory=dict)
    suitable_financial_products: List[str] = Field(default_factory=list)
    risk_warnings: List[str] = Field(default_factory=list)


class PersonalizedInsights(BaseModel):
    """个性化insight"""
    user_id: str
    # userbehaviorinsight
    behavioral_insights: List[str] = Field(default_factory=list)
    # 风险insight  
    risk_insights: List[str] = Field(default_factory=list)
    # 机会insight
    opportunity_insights: List[str] = Field(default_factory=list)
    # warntip
    warning_insights: List[str] = Field(default_factory=list)
    
    # recommendation权重（基于user画像adjust）
    recommendation_weights: Dict[str, float] = Field(default_factory=dict)
    
    # generatetime
    generated_at: datetime = Field(default_factory=datetime.now)


class EnhancedUserPortfolio(UserPortfolio):
    """enhance的userportfolio（包含画像和behavioranalysis）"""
    user_profile: Optional[UserProfile] = None
    transaction_behavior: Optional[TransactionBehavior] = None
    risk_profile: Optional[RiskProfile] = None
    personalized_insights: Optional[PersonalizedInsights] = None
    
    @classmethod
    def from_bq_dict_enhanced(cls, data: Dict[str, Any]) -> "EnhancedUserPortfolio":
        """从BigQuerydatacreateenhanceportfolio"""
        # 先create基础portfolio
        base_portfolio = UserPortfolio.from_bq_dict(data)
        
        # createenhanceversion
        enhanced = cls(
            user_id=base_portfolio.user_id,
            total_assets=base_portfolio.total_assets,
            assets=base_portfolio.assets,
            risk_profile=base_portfolio.risk_profile,
            portfolio_performance=base_portfolio.portfolio_performance,
            last_updated=base_portfolio.last_updated,
            data_source=base_portfolio.data_source,
            total_estimated_value=base_portfolio.total_estimated_value
        )
        
        # add画像data（if存在）
        if 'user_profile' in data:
            enhanced.user_profile = UserProfile(**data['user_profile'])
        
        if 'transaction_behavior' in data:
            enhanced.transaction_behavior = TransactionBehavior(**data['transaction_behavior'])
            
        if 'risk_profile_enhanced' in data:
            enhanced.risk_profile = RiskProfile(**data['risk_profile_enhanced'])
            
        if 'personalized_insights' in data:
            enhanced.personalized_insights = PersonalizedInsights(**data['personalized_insights'])
        
        return enhanced