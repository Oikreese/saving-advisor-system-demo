from fastapi import APIRouter, HTTPException, Depends, Query
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta

from app.core.logging import logger
from app.services.core.analysis_service import get_core_analysis_service, CoreAnalysisService
# BigQuery関連 インポート 保持し、directlyBigQuery クエリするエンドPoints use
from app.services.bigquery.enhanced_client import get_enhanced_bigquery_client, EnhancedBigQueryClient
from app.models.assets import (
    UserPortfolio, UserProfile, TransactionBehavior, RiskProfile, 
    PersonalizedInsights, EnhancedUserPortfolio
)

router = APIRouter()

@router.get("/general/{user_id}", response_model=str)
async def get_general_analysis(
    user_id: str, 
    core_service: CoreAnalysisService = Depends(get_core_analysis_service)
):
    """
    user 総合portfolioanalysis 取得 - Firestore リアルタイムdata 基づく
    共有コアanalysisサービス use
    """
    logger.info(f"総合analysisAPI呼び出し: user_id={user_id}")
    try:
        # コアanalysisサービス 呼び出し
        result = await core_service.analyze_general_portfolio(user_id, allow_empty_portfolio=False)
        
        if not result.success:
            logger.error(f"総合analysisfailed: {result.error_message}")
            raise HTTPException(status_code=500, detail=result.error_message)
        
        logger.info(f"総合analysissuccess: user_id={user_id}")
        return result.analysis_summary

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"総合analysis中 エラー 発生: {e}")
        raise HTTPException(status_code=500, detail=f"総合analysis generate failed: {e}")


# ============== enhanceanalysis機能 - すべて BigQuerydata 最大限 utilize ==============

@router.get("/enhanced-portfolio/{user_id}", response_model=Dict[str, Any])
async def get_enhanced_user_analysis(
    user_id: str,
    core_service: CoreAnalysisService = Depends(get_core_analysis_service)
) -> Dict[str, Any]:
    """
    user enhanceanalysisレポート 取得
    共有コアanalysisサービス use
    
    統合in容：
    - 基本assetdata
    - user 完全なプロファイル（人口統計情報）
    - 取引行動 詳細analysis
    - 多次元リスク評価
    - パーソナライズされたインサイト 提案
    """
    try:
        logger.info(f"🎯 enhanceuseranalysis 開始: user_id={user_id}")
        
        # コアanalysisサービス 呼び出し
        result = await core_service.get_enhanced_user_analysis(user_id)
        
        if not result:
            raise HTTPException(
                status_code=404, 
                detail=f"user {user_id}  data 見つ from ないか、analysis failed"
            )
        
        logger.info(f"✅ enhanceuseranalysis 完了: user_id={user_id}")
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ enhanceuseranalysis failed: user_id={user_id}, error={e}")
        raise HTTPException(
            status_code=500, 
            detail=f"enhanceanalysis failed: {str(e)}"
        )

@router.get("/user-profile/{user_id}", response_model=Dict[str, Any])
async def get_user_profile_analysis(
    user_id: str,
    core_service: CoreAnalysisService = Depends(get_core_analysis_service)
):
    """userプロファイルanalysis 取得（usersおよびv2_customerテーブル 基づく）"""
    try:
        logger.info(f"userプロファイルanalysis 取得: {user_id}")
        
        # コアanalysisサービス 呼び出し
        result = await core_service.get_user_profile_analysis(user_id)
        
        if not result:
            raise HTTPException(
                status_code=404, 
                detail=f"user {user_id}  プロファイルdata not found"
            )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"userプロファイル 取得 failed: {e}")
        raise HTTPException(status_code=500, detail=f"プロファイルanalysis failed: {str(e)}")

@router.get("/transaction-behavior/{user_id}", response_model=Dict[str, Any])
async def get_transaction_behavior_analysis(
    user_id: str,
    core_service: CoreAnalysisService = Depends(get_core_analysis_service)
):
    """取引行動analysis 取得（transaction_evidencesテーブル 基づく）"""
    try:
        logger.info(f"取引行動 analysis: {user_id}")
        
        # コアanalysisサービス 呼び出し
        result = await core_service.get_transaction_behavior_analysis(user_id)
        
        if not result:
            raise HTTPException(
                status_code=404, 
                detail=f"user {user_id}  取引記録 not available"
            )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"取引行動 analysis failed: {e}")
        raise HTTPException(status_code=500, detail=f"行動analysis failed: {str(e)}")

@router.post("/initialize-analytics")
async def initialize_bigquery_analytics(
    bq_client: EnhancedBigQueryClient = Depends(get_enhanced_bigquery_client)
):
    """BigQueryanalysisテーブル 初期化（バッチ処理analysisテーブル 作成）"""
    try:
        logger.info("🚀 BigQueryanalysisテーブル 初期化中...")
        
        success = await bq_client.create_bigquery_analytics_tables()
        
        if success:
            return {
                "status": "success",
                "message": "BigQueryanalysisテーブル 作成 完了しました",
                "tables_created": [
                    "user_behavior_analytics",
                    "market_trend_analytics", 
                    "user_risk_analytics"
                ],
                "created_at": datetime.now().isoformat()
            }
        else:
            raise HTTPException(
                status_code=500,
                detail="analysisテーブル 作成 failed"
            )
            
    except Exception as e:
        logger.error(f"analysisテーブル 初期化 failed: {e}")
        raise HTTPException(
            status_code=500, 
            detail=f"初期化 failed: {str(e)}"
        )

@router.get("/user-segments")
async def get_user_segments(
    bq_client: EnhancedBigQueryClient = Depends(get_enhanced_bigquery_client)
):
    """userセグメントanalysis 取得（全data 総合analysis 基づく）"""
    try:
        # ここ analysisテーブル based onuserセグメント クエリ append きます
        # 例：高価値user、アクティブuser、リスクuserなど セグメント
        
        return {
            "message": "userセグメントanalysis機能 準備完了 す",
            "available_segments": [
                "high_value_traders",
                "frequent_buyers", 
                "active_sellers",
                "risk_tolerant_users",
                "conservative_investors",
                "new_user_prospects"
            ],
            "note": "transaction_evidences、users、v2_customer 総合analysis based onます"
        }
        
    except Exception as e:
        logger.error(f"userセグメントanalysis failed: {e}")
        raise HTTPException(status_code=500, detail=f"セグメントanalysis failed: {str(e)}")


# ============== 補助関数 ==============

def get_risk_interpretation(risk_level: str) -> str:
    """リスクレベル 解釈"""
    interpretations = {
        "conservative": "保守型 - 安定した収益 好み、リスク許容度 低い",
        "moderate": "バランス型 - 適度な収益 追求し、中程度 リスク 許容 きる",
        "aggressive": "積極型 - 高い収益 追求し、高いリスク許容度 持つ"
    }
    return interpretations.get(risk_level, "不明なリスクタイプ")

def generate_priority_actions(portfolio: EnhancedUserPortfolio) -> List[str]:
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

def generate_next_steps(portfolio: EnhancedUserPortfolio) -> List[str]:
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

def calculate_account_maturity(registration_date: Optional[datetime]) -> str:
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

def get_demographic_segment(profile: UserProfile) -> str:
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

def get_engagement_level(profile: UserProfile) -> str:
    """userエンゲージメントレベル 取得"""
    # ここ  より多く data based onエンゲージメント 判断 きます
    # 一時  基本情報 判断
    if profile.basic_info.get("description"):
        return "high_engagement"
    elif profile.basic_info.get("nickname"):
        return "medium_engagement"
    else:
        return "low_engagement"

def classify_user_type(behavior: TransactionBehavior) -> str:
    """userタイプ 分類"""
    if behavior.buyer_seller_ratio > 2:
        return "primary_buyer"
    elif behavior.buyer_seller_ratio < 0.5:
        return "primary_seller"
    elif behavior.total_transactions > 15:
        return "active_trader"
    else:
        return "casual_user"

def classify_activity_level(behavior: TransactionBehavior) -> str:
    """活動レベル 分類"""
    if behavior.transaction_frequency > 10:
        return "highly_active"
    elif behavior.transaction_frequency > 5:
        return "moderately_active"
    elif behavior.transaction_frequency > 2:
        return "occasionally_active"
    else:
        return "low_activity"

def classify_spending_pattern(behavior: TransactionBehavior) -> str:
    """消費パターン 分類"""
    if behavior.avg_transaction_amount > 5000:
        return "high_value_spender"
    elif behavior.avg_transaction_amount > 2000:
        return "medium_value_spender"
    else:
        return "budget_conscious"

def classify_reliability(behavior: TransactionBehavior) -> str:
    """信頼性 分類"""
    if behavior.completed_transaction_rate > 0.95 and behavior.cancellation_rate < 0.05:
        return "highly_reliable"
    elif behavior.completed_transaction_rate > 0.85 and behavior.cancellation_rate < 0.15:
        return "reliable"
    elif behavior.completed_transaction_rate > 0.7:
        return "moderately_reliable"
    else:
        return "needs_improvement"

def generate_platform_comparison(behavior: TransactionBehavior) -> Dict[str, str]:
    """プラットフォーム比較指標 generate"""
    # ここ  実際 プラットフォーム平均data 基づくべき す
    # 一時  サンプル比較 provide
    return {
        "transaction_frequency": "above_average" if behavior.transaction_frequency > 6 else "below_average",
        "completion_rate": "excellent" if behavior.completed_transaction_rate > 0.9 else "good" if behavior.completed_transaction_rate > 0.8 else "needs_improvement",
        "avg_transaction_value": "high" if behavior.avg_transaction_amount > 3000 else "medium" if behavior.avg_transaction_amount > 1500 else "low"
    }
