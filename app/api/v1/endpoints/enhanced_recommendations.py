"""
拡張recommendationAPIエンドPoints - BigQuery 深いinsight 統合したインテリジェントrecommendationシステム

BigQueryanalysisエンジン userインサイト recommendationシステム 最大限 utilizeするmethod 例：
1. userセグメント 基づく差別化されたrecommendation戦略
2. 解約リスク warn 積極 な介入
3. 成長ポテンシャル 特定 パーソナライズされたガイダンス
4. 市場トレンド based on動 なrecommendationadjust
"""

from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks, Query
from typing import List, Optional, Any, Dict
from datetime import datetime
import logging
import asyncio

from app.models.assets import UserPortfolio
from app.models.recommendations import MultiAgentResponse
from app.agents.multi_agent_system import MultiAgentSystem
from app.services.firestore.firestore_primary_service import get_firestore_primary_service, FirestorePrimaryService
from app.services.bigquery.insights_service_optimized import get_optimized_insights_service as get_bigquery_insights_service, OptimizedInsightsService as BigQueryInsightsService
from app.core.logging import logger

router = APIRouter()

# グローバルインスタンス
multi_agent_system = MultiAgentSystem()


@router.get("/intelligent-analyze/{user_id}", response_model=MultiAgentResponse)
async def intelligent_portfolio_analysis(
    user_id: str,
    force_fresh: bool = False,
    include_market_trends: bool = True,
    firestore_service: FirestorePrimaryService = Depends(get_firestore_primary_service),
    insights_service: BigQueryInsightsService = Depends(get_bigquery_insights_service)
):
    """
    インテリジェントportfolioanalysis - BigQuery 深いinsight 統合

    主な機能：
    ✨ userセグメント based onパーソナライズrecommendation戦略
    ⚠️ 解約リスク warn 介入提案
    📈 成長ポテンシャル 特定 ガイダンス戦略
    📊 市場トレンド 感知した動 adjust
    🎯 data駆動型 精密なrecommendation
    """
    try:
        start_time = datetime.now()
        logger.info(f"🧠 インテリジェントportfolioanalysis 開始: user_id={user_id}")
        
        # 1. キャッシュ 確認（強制リフレッシュ ない場合）
        if not force_fresh:
            cached_analysis = await firestore_service.get_recent_ai_analysis(
                user_id, 'intelligent_portfolio_analysis', max_age_hours=6  # インテリジェンス 反映するforキャッシュ時間 短縮
            )
            if cached_analysis:
                analysis_time = (datetime.now() - start_time).total_seconds() * 1000
                logger.info(f"キャッシュされたインテリジェントanalysis 返します ({analysis_time:.2f}ms)")
                return _construct_response_from_cache(cached_analysis, user_id)
        
        # 2. data 並行して取得：Firestore リアルタイムdata + BigQuery 深いinsight
        logger.info("🔄 リアルタイムdata 深いinsight 並行して取得中...")
        
        portfolio_task = firestore_service.get_user_portfolio(user_id)
        insights_task = insights_service.get_user_comprehensive_insights(user_id)
        
        portfolio, user_insights = await asyncio.gather(portfolio_task, insights_task)
        
        # 3. enhancedanalysiscontext build
        enhanced_context = _build_enhanced_analysis_context(portfolio, user_insights, include_market_trends)
        
        logger.info(f"📊 userインサイト概要: セグメント={user_insights.get('user_segment')}, "
                   f"解約リスク={user_insights.get('churn_risk', {}).get('score')}, "
                   f"成長ポテンシャル={user_insights.get('growth_potential', {}).get('score')}")
        
        # 4. インテリジェントanalysis execute（BigQuery insight 統合）
        analysis_result = await multi_agent_system.analyze_portfolio_with_insights(
            portfolio, enhanced_context
        )
        
        # 5. post-processing：パーソナライズされた提案 リスクwarn append
        enhanced_result = _enhance_analysis_result(analysis_result, user_insights, portfolio)
        
        # 6. analysis結果 save
        session_id = await firestore_service.save_ai_analysis(
            user_id=user_id,
            session_type='intelligent_portfolio_analysis',
            input_data={
                'portfolio_total_value': portfolio.total_assets,
                'user_segment': user_insights.get('user_segment'),
                'churn_risk_score': user_insights.get('churn_risk', {}).get('score'),
                'growth_potential_score': user_insights.get('growth_potential', {}).get('score')
            },
            ai_response=enhanced_result.model_dump(),
            processing_time_ms=int((datetime.now() - start_time).total_seconds() * 1000)
        )
        
        # 7. 非同期処理：リスクuserへ 介入
        if user_insights.get('churn_risk', {}).get('score', 0) > 70:
            # レスポンス ブロックせず、非同期 リスクuserケアプロセス トリガー
            asyncio.create_task(_trigger_churn_prevention_workflow(user_id, user_insights))
        
        analysis_time = (datetime.now() - start_time).total_seconds() * 1000
        logger.info(f"✅ インテリジェントanalysis完了: user_id={user_id} ({analysis_time:.2f}ms), session_id={session_id}")
        
        return enhanced_result
        
    except Exception as e:
        logger.error(f"❌ インテリジェントportfolioanalysisfailed: {e}")
        # 基本analysis fallback
        return await _fallback_to_basic_analysis(user_id, firestore_service)


@router.get("/segment-insights/{user_segment}")
async def get_segment_insights(
    user_segment: str,
    limit: int = Query(default=20, ge=1, le=100),
    insights_service: BigQueryInsightsService = Depends(get_bigquery_insights_service)
):
    """
    userセグメント インサイト 取得 - ビジネス上 意思決定 サポート
    
    用途：
    📈 様々なuserグループ 特徴 理解する
    🎯 ターゲット 絞った運営戦略 策定する
    💰 各セグメントグループ 価値 評価する
    """
    try:
        logger.info(f"userセグメント インサイト 取得: {user_segment}")
        
        # セグメント統計 取得
        segment_stats = await insights_service.get_segment_statistics()
        
        if user_segment not in segment_stats.get('segments', {}):
            raise HTTPException(status_code=404, detail=f"userセグメント '{user_segment}'  existsしません")
        
        # セグメントタイプ based onuserlist 取得（サンプル実装）
        segment_info = segment_stats['segments'][user_segment]
        
        # セグメントインサイトレポート generate
        insights_report = _generate_segment_insights_report(user_segment, segment_info, segment_stats)
        
        return {
            "segment": user_segment,
            "statistics": segment_info,
            "insights": insights_report,
            "recommendations": _get_segment_management_recommendations(user_segment),
            "generated_at": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"セグメント インサイト取得failed: {e}")
        raise HTTPException(status_code=500, detail="セグメント インサイト取得 failed")


@router.get("/risk-management/high-risk-users")
async def get_high_risk_users_for_intervention(
    limit: int = Query(default=50, ge=1, le=200),
    min_risk_score: int = Query(default=70, ge=0, le=100),
    insights_service: BigQueryInsightsService = Depends(get_bigquery_insights_service)
):
    """
    高リスクuserlist 取得 - 積極 な介入 サポート
    
    用途：
    ⚠️ 解約しそうな高価値user 特定する
    📞 カスタマーサポート よる積極 なケアプロセス トリガーする
    🎁 ターゲット 絞った引き留め策 provideする
    """
    try:
        logger.info(f"高リスクuserlist 取得, リスク閾値: {min_risk_score}")
        
        # 高リスクuser 取得
        high_risk_users = await insights_service.get_high_risk_users(limit)
        
        # リスクスコア フィルタリング
        filtered_users = [
            user for user in high_risk_users 
            if user.get('churn_risk_score', 0) >= min_risk_score
        ]
        
        # 各user 介入提案 generate
        intervention_plan = []
        for user in filtered_users[:limit]:
            user_plan = {
                "user_id": user["user_id"],
                "risk_score": user["churn_risk_score"],
                "risk_category": user["risk_category"],
                "days_inactive": user.get("days_since_last_transaction", 0),
                "intervention_priority": _calculate_intervention_priority(user),
                "recommended_actions": _generate_intervention_actions(user),
                "expected_timeline": "24-48時間以in execute"
            }
            intervention_plan.append(user_plan)
        
        # 優first度 ソート
        intervention_plan.sort(key=lambda x: x["intervention_priority"], reverse=True)
        
        return {
            "high_risk_count": len(filtered_users),
            "intervention_plan": intervention_plan,
            "summary": {
                "urgent_cases": len([u for u in filtered_users if u["churn_risk_score"] >= 90]),
                "high_priority": len([u for u in filtered_users if 80 <= u["churn_risk_score"] < 90]),
                "medium_priority": len([u for u in filtered_users if 70 <= u["churn_risk_score"] < 80])
            },
            "generated_at": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"高リスクuser 取得failed: {e}")
        raise HTTPException(status_code=500, detail="高リスクuser 取得 failed")


@router.get("/growth-opportunities/high-potential-users") 
async def get_high_potential_users_for_activation(
    limit: int = Query(default=50, ge=1, le=200),
    min_potential_score: int = Query(default=70, ge=0, le=100),
    insights_service: BigQueryInsightsService = Depends(get_bigquery_insights_service)
):
    """
    高成長ポテンシャルuserlist 取得 - 成長活性化 サポート
    
    用途：
    🚀 高い成長ポテンシャル 持つuser 特定する
    💰 パーソナライズされた成長戦略 策定する
    📈 user ライフタイムバリュー 向上させる
    """
    try:
        logger.info(f"高ポテンシャルuserlist 取得, ポテンシャル閾値: {min_potential_score}")
        
        # 高ポテンシャルuser 取得
        high_potential_users = await insights_service.get_high_potential_users(limit)
        
        # ポテンシャルスコア フィルタリング
        filtered_users = [
            user for user in high_potential_users 
            if user.get('growth_potential_score', 0) >= min_potential_score
        ]
        
        # 各user 活性化プラン generate
        activation_plan = []
        for user in filtered_users[:limit]:
            user_plan = {
                "user_id": user["user_id"],
                "potential_score": user["growth_potential_score"],
                "recommended_strategy": user["recommended_strategy"],
                "potential_growth": float(user.get("potential_growth", 0)),
                "activation_priority": _calculate_activation_priority(user),
                "growth_actions": _generate_growth_actions(user),
                "expected_roi": _estimate_activation_roi(user)
            }
            activation_plan.append(user_plan)
        
        # ポテンシャル ROI ソート
        activation_plan.sort(key=lambda x: (x["potential_score"], x["expected_roi"]), reverse=True)
        
        return {
            "high_potential_count": len(filtered_users),
            "activation_plan": activation_plan,
            "summary": {
                "aggressive_growth_candidates": len([u for u in filtered_users if u["recommended_strategy"] == "aggressive_growth"]),
                "moderate_growth_candidates": len([u for u in filtered_users if u["recommended_strategy"] == "moderate_growth"]),
                "total_potential_value": sum(float(u.get("potential_growth", 0)) for u in filtered_users)
            },
            "generated_at": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"高ポテンシャルuser 取得failed: {e}")
        raise HTTPException(status_code=500, detail="高ポテンシャルuser 取得 failed")


@router.post("/trigger-interventions/{user_id}")
async def trigger_user_intervention(
    user_id: str,
    intervention_type: str = Query(..., description="介入タイプ: churn_prevention, growth_activation, re_engagement"),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    firestore_service: FirestorePrimaryService = Depends(get_firestore_primary_service),
    insights_service: BigQueryInsightsService = Depends(get_bigquery_insights_service)
):
    """
    user介入プロセス 手動 トリガー
    
    用途：
    🎯 カスタマーサポート 特定 user ケアプロセス 手動 トリガー
    ⚡ リアルタイム 状況 応じて介入戦略 adjust
    📊 介入効果 記録し、後 analysis 役立てる
    """
    try:
        logger.info(f"user介入 トリガー: user_id={user_id}, type={intervention_type}")
        
        # userインサイト 取得
        user_insights = await insights_service.get_user_comprehensive_insights(user_id)
        
        # 介入タイプ 適用性 検証
        if not _validate_intervention_applicability(intervention_type, user_insights):
            raise HTTPException(
                status_code=400, 
                detail=f"user{user_id} {intervention_type}タイプ 介入  適していません"
            )
        
        # バックグラウンドタスク appendして具体 な介入 execute
        background_tasks.add_task(
            _execute_intervention_workflow,
            user_id, 
            intervention_type, 
            user_insights,
            firestore_service
        )
        
        return {
            "user_id": user_id,
            "intervention_type": intervention_type,
            "status": "triggered",
            "estimated_execution_time": "5-10分",
            "user_segment": user_insights.get("user_segment"),
            "risk_score": user_insights.get("churn_risk", {}).get("score"),
            "potential_score": user_insights.get("growth_potential", {}).get("score"),
            "triggered_at": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"user介入 トリガーfailed: {e}")
        raise HTTPException(status_code=500, detail="user介入 トリガー failed")


# ==================== 補助関数 ====================

def _build_enhanced_analysis_context(
    portfolio: UserPortfolio, 
    user_insights: Dict[str, Any], 
    include_market_trends: bool
) -> Dict[str, Any]:
    """enhancedanalysiscontext build"""
    context = {
        # 基本情報
        "portfolio_value": portfolio.total_assets,
        "asset_count": len(portfolio.assets),
        
        # userセグメント スコア
        "user_segment": user_insights.get("user_segment", "unknown"),
        "user_scores": user_insights.get("scores", {}),
        
        # リスク評価
        "churn_risk": user_insights.get("churn_risk", {}),
        "risk_prevention_needed": user_insights.get("churn_risk", {}).get("score", 0) > 50,
        
        # 成長ポテンシャル
        "growth_potential": user_insights.get("growth_potential", {}),
        "growth_strategy": user_insights.get("growth_potential", {}).get("strategy", "moderate_growth"),
        
        # asset配分インサイト
        "allocation_insights": user_insights.get("asset_allocation", {}),
        
        # パーソナライズされたrecommendation
        "personalized_recommendations": user_insights.get("personalized_recommendations", []),
        
        # data品質
        "data_confidence": user_insights.get("data_quality", {}).get("confidence", 0.5)
    }
    
    # 市場トレンドcontext
    if include_market_trends:
        market_context = user_insights.get("market_context", {})
        context["market_trends"] = {
            "trending_categories": market_context.get("trending_categories", []),
            "market_sentiment": market_context.get("market_sentiment", "neutral"),
            "relevant_trends": market_context.get("relevant_to_user", [])
        }
    
    return context


def _enhance_analysis_result(
    analysis_result: MultiAgentResponse, 
    user_insights: Dict[str, Any], 
    portfolio: UserPortfolio
) -> MultiAgentResponse:
    """analysis結果 enhanceし、パーソナライズされたインサイト append"""
    
    # リスクwarn append
    risk_score = user_insights.get("churn_risk", {}).get("score", 0)
    if risk_score > 70:
        risk_warning = f"⚠️ 解約リスクwarn：こ user 解約リスク 高い す（{risk_score}点）。すぐ note 払うこ  お勧めします"
        analysis_result.overall_assessment = risk_warning + "\n\n" + analysis_result.overall_assessment
    
    # 成長機会 ヒント append
    growth_score = user_insights.get("growth_potential", {}).get("score", 0)
    if growth_score > 70:
        growth_opportunity = f"🚀 成長機会：こ user 高い成長ポテンシャル 持っています（{growth_score}点）。積極 な成長戦略 recommendationします"
        if not analysis_result.overall_assessment.startswith("⚠️"):
            analysis_result.overall_assessment = growth_opportunity + "\n\n" + analysis_result.overall_assessment
    
    # パーソナライズされたrecommendation 統合
    personalized_recs = user_insights.get("personalized_recommendations", [])
    if personalized_recs:
        analysis_result.consensus_recommendations.extend([
            f"🎯 パーソナライズ提案: {rec}" for rec in personalized_recs[:2]
        ])
    
    return analysis_result


# _get_portfolio_from_firestore 関数  FirestorePrimaryService.get_user_portfolio  移動しました


async def _fallback_to_basic_analysis(user_id: str, firestore_service: FirestorePrimaryService) -> MultiAgentResponse:
    """基本analysis fallback"""
    try:
        logger.info(f"基本analysis fallback: {user_id}")
        portfolio = await firestore_service.get_user_portfolio(user_id)
        
        # 基本 マルチagentanalysis use
        result = await multi_agent_system.analyze_portfolio(portfolio)
        
        # fallbackしたこ  示すヒント append
        result.overall_assessment = "🔄 基本analysisモード use中（詳細インサイトサービス 一時  利用 きません）\n\n" + result.overall_assessment
        
        return result
        
    except Exception as e:
        logger.error(f"基本analysisもfailed: {e}")
        raise HTTPException(status_code=500, detail="portfolioanalysisサービス 一時  利用 きません")


def _construct_response_from_cache(cached_analysis: Dict[str, Any], user_id: str) -> MultiAgentResponse:
    """キャッシュ from レスポンス build"""
    ai_response = cached_analysis.get('ai_response', {})
    return MultiAgentResponse(
        user_id=user_id,
        analyses=ai_response.get('analyses', []),
        consensus_recommendations=ai_response.get('consensus_recommendations', []),
        conflicting_opinions=ai_response.get('conflicting_opinions', []),
        overall_assessment=ai_response.get('overall_assessment', ''),
        generated_at=datetime.fromisoformat(cached_analysis.get('created_at'))
    )


# userセグメント管理関連 関数
def _generate_segment_insights_report(segment: str, segment_info: Dict, all_stats: Dict) -> Dict[str, Any]:
    """セグメントインサイトレポート generate"""
    total_users = all_stats.get('total_users', 0)
    segment_count = segment_info.get('count', 0)
    percentage = (segment_count / total_users * 100) if total_users > 0 else 0
    
    return {
        "market_share": f"{percentage:.1f}%",
        "avg_value": segment_info.get('avg_value_score', 0),
        "characteristics": _get_segment_characteristics(segment),
        "business_impact": _assess_segment_business_impact(segment, segment_info),
        "optimization_opportunities": _identify_optimization_opportunities(segment)
    }


def _get_segment_characteristics(segment: str) -> List[str]:
    """セグメント 特徴 取得"""
    characteristics = {
        "champions": ["高価値", "高アクティブ", "高ロイヤルティ", "収益貢献最大"],
        "loyal_customers": ["安定価値", "継続 アクティブ", "ブランドへ 忠誠心"],
        "potential_loyalists": ["アクティブ度高い", "価値成長中", "育成ポテンシャル大"],
        "at_risk": ["価値低下", "アクティブ度低下", "ケア 必要"],
        "lost": ["利用stop", "呼び戻し戦略 必要"]
    }
    return characteristics.get(segment, ["さらなるanalysis 必要"])


def _get_segment_management_recommendations(segment: str) -> List[str]:
    """セグメント管理 recommendations 取得"""
    recommendations = {
        "champions": [
            "VIP専用サービス 製品 provide",
            "製品テスト feedbackへ 招待",
            "紹介報奨プログラム 実施"
        ],
        "loyal_customers": [
            "現在 サービス品質 維持", 
            "ロイヤルティ報奨 provide",
            "new機能 製品 プロモーション"
        ],
        "potential_loyalists": [
            "user教育 ガイダンス enhance",
            "より多く 投資選択肢 provide",
            "パーソナライズrecommendationアルゴリズム 最適化"
        ],
        "at_risk": [
            "積極 なカスタマーケア",
            "専用 割引 インセンティブ provide",
            "利用上 障害 理解し解決する"
        ],
        "lost": [
            "呼び戻しキャンペーン 割引", 
            "再アクティベーションプロセス 簡素化",
            "解約理由 理解し改善する"
        ]
    }
    return recommendations.get(segment, ["ターゲット 絞った戦略 策定"])


# リスク介入関連 関数
def _calculate_intervention_priority(user: Dict[str, Any]) -> int:
    """介入 優first度 計算 (0-100)"""
    risk_score = user.get('churn_risk_score', 0)
    days_inactive = user.get('days_since_last_transaction', 0)
    
    # 基本 な優first度 リスクスコア 基づく
    priority = risk_score
    
    # 非アクティブ日数 重み付け
    if days_inactive > 60:
        priority += 20
    elif days_inactive > 30:
        priority += 10
    
    return min(100, priority)


def _generate_intervention_actions(user: Dict[str, Any]) -> List[str]:
    """介入アクション 提案 generate"""
    risk_score = user.get('churn_risk_score', 0)
    
    if risk_score >= 90:
        return [
            "🔥 緊急：カスタマーサポート 責任者 directly連絡",
            "🎁 最高レベル 引き留めオファー provide",
            "📞 専任担当者 よるフォローアップ 手配"
        ]
    elif risk_score >= 80:
        return [
            "📞 カスタマーサポート from 状況確認 連絡",
            "💰 パーソナライズされた割引プラン provide",
            "📧 ケアメール 送信"
        ]
    elif risk_score >= 70:
        return [
            "📱 パーソナライズされたコンテンツ プッシュnotify",
            "🎯 関連製品 recommendation provide",
            "📊 利用習慣 変化 analysis"
        ]
    else:
        return ["📈 user アクティビティ変化 監視"]


# 成長活性化関連 関数
def _calculate_activation_priority(user: Dict[str, Any]) -> int:
    """活性化 優first度 計算"""
    potential_score = user.get('growth_potential_score', 0)
    potential_growth = user.get('potential_growth', 0)
    
    # ポテンシャルスコア 期待成長 基づく
    priority = potential_score
    
    # 期待収益 重み付け
    if potential_growth > 50000:  # 5万円以上
        priority += 15
    elif potential_growth > 20000:  # 2万円以上
        priority += 10
    
    return min(100, priority)


def _generate_growth_actions(user: Dict[str, Any]) -> List[str]:
    """成長アクション 提案 generate"""
    strategy = user.get('recommended_strategy', 'moderate_growth')
    
    strategies = {
        'aggressive_growth': [
            "🚀 高収益投資商品 recommendation",
            "💡 投資コンサルティングサービス provide",
            "📈 heightな投資ツール 紹介"
        ],
        'moderate_growth': [
            "📊 バランス型投資portfolio recommendation",
            "🎯 カスタマイズされた投資アドバイス provide",
            "📚 投資教育コンテンツ 配信"
        ],
        'conservative_growth': [
            "🛡️ 安定型商品 recommendation",
            "💰 元本 安全性 強調",
            "📖 リスク教育 provide"
        ]
    }
    
    return strategies.get(strategy, ["📈 個人 成長計画 策定"])


def _estimate_activation_roi(user: Dict[str, Any]) -> float:
    """活性化 ROI 推定"""
    potential_growth = user.get('potential_growth', 0)
    potential_score = user.get('growth_potential_score', 0)
    
    # 簡略化されたROI推定：期待成長 × success確率
    success_probability = potential_score / 100
    estimated_roi = potential_growth * success_probability * 0.1  # 10% 収益率 仮定
    
    return round(estimated_roi, 2)


# 介入ワークフロー関連 関数
def _validate_intervention_applicability(intervention_type: str, user_insights: Dict[str, Any]) -> bool:
    """介入タイプ 適用性 検証"""
    if intervention_type == 'churn_prevention':
        return user_insights.get('churn_risk', {}).get('score', 0) > 50
    elif intervention_type == 'growth_activation':
        return user_insights.get('growth_potential', {}).get('score', 0) > 60
    elif intervention_type == 're_engagement':
        return user_insights.get('scores', {}).get('activity', 0) < 40
    
    return False


async def _execute_intervention_workflow(
    user_id: str,
    intervention_type: str, 
    user_insights: Dict[str, Any],
    firestore_service: FirestorePrimaryService
):
    """具体 な介入ワークフロー execute"""
    logger.info(f"介入ワークフロー execute: user_id={user_id}, type={intervention_type}")
    
    try:
        # 介入ログ 記録
        intervention_log = {
            "user_id": user_id,
            "intervention_type": intervention_type,
            "user_segment": user_insights.get("user_segment"),
            "trigger_time": datetime.now().isoformat(),
            "status": "executing"
        }
        
        # 介入タイプ 応じて異なるロジック execute
        if intervention_type == 'churn_prevention':
            await _execute_churn_prevention(user_id, user_insights, firestore_service)
        elif intervention_type == 'growth_activation':
            await _execute_growth_activation(user_id, user_insights, firestore_service)
        elif intervention_type == 're_engagement':
            await _execute_re_engagement(user_id, user_insights, firestore_service)
        
        intervention_log["status"] = "completed"
        intervention_log["completed_time"] = datetime.now().isoformat()
        
        # 介入記録 Firestore save（後 効果analysis for）
        await firestore_service._mark_for_etl(f"interventions/{user_id}", intervention_log)
        
        logger.info(f"介入ワークフロー execute完了: user_id={user_id}")
        
    except Exception as e:
        logger.error(f"介入ワークフロー executefailed: user_id={user_id}, error={e}")


async def _execute_churn_prevention(user_id: str, user_insights: Dict[str, Any], firestore_service: FirestorePrimaryService):
    """解約防止プロセス execute"""
    # ここ 具体 な解約防止ロジック 実装
    # 例：プッシュnotify 送信、クーポン作成、カスタマーサポート フォローアップ手配など
    logger.info(f"解約防止策 execute: {user_id}")
    
    # 例：特別なケア 必要なマーク save
    care_plan = {
        "user_id": user_id,
        "care_type": "churn_prevention",
        "priority": "high",
        "actions_needed": [
            "カスタマーサポート from 積極 な連絡",
            "専用 割引 provide",
            "利用上 問題点 ヒアリング"
        ],
        "created_at": datetime.now().isoformat()
    }
    
    # Firestore saveし、後続 ビジネスプロセス トリガー
    await firestore_service._mark_for_etl(f"care_plans/{user_id}", care_plan)


async def _execute_growth_activation(user_id: str, user_insights: Dict[str, Any], firestore_service: FirestorePrimaryService):
    """成長活性化プロセス execute"""
    logger.info(f"成長活性化策 execute: {user_id}")
    
    growth_plan = {
        "user_id": user_id,
        "activation_type": "growth_potential",
        "recommended_strategy": user_insights.get("growth_potential", {}).get("strategy"),
        "target_actions": [
            "高ポテンシャル投資 recommendation",
            "specialist なコンサルティング provide",
            "パーソナライズされた製品プロモーション"
        ],
        "created_at": datetime.now().isoformat()
    }
    
    await firestore_service._mark_for_etl(f"growth_plans/{user_id}", growth_plan)


async def _execute_re_engagement(user_id: str, user_insights: Dict[str, Any], firestore_service: FirestorePrimaryService):
    """再エンゲージメントプロセス execute"""
    logger.info(f"再エンゲージメント策 execute: {user_id}")
    
    engagement_plan = {
        "user_id": user_id,
        "engagement_type": "re_activation",
        "activity_score": user_insights.get("scores", {}).get("activity", 0),
        "target_actions": [
            "興味深いコンテンツ プッシュnotify",
            "簡単なタスク provide",
            "復帰userへ 報酬"
        ],
        "created_at": datetime.now().isoformat()
    }
    
    await firestore_service._mark_for_etl(f"engagement_plans/{user_id}", engagement_plan)


async def _trigger_churn_prevention_workflow(user_id: str, user_insights: Dict[str, Any]):
    """非同期 解約防止ワークフロー トリガー"""
    logger.warning(f"🚨 自動解約防止ワークフロー トリガー: user_id={user_id}")
    
    # ここ 外部システム  連携 可能
    # 例：
    # - カスタマーサポートチームへ アラート送信
    # - カスタマーサポート チケット 自動作成
    # - マーケティングオートメーションプロセス トリガー
    # - 緊急ケアメールやプッシュnotify 送信
    
    # 実装例：自動トリガーされた解約防止策 記録
    await asyncio.sleep(1)  # 非同期処理 シミュレート
    logger.info(f"自動解約防止ワークフロー 記録されました: {user_id}")


# ツール関数
def _assess_segment_business_impact(segment: str, segment_info: Dict) -> str:
    """セグメントグループ ビジネスへ 影響 評価"""
    if segment in ['champions', 'loyal_customers']:
        return "高価値グループ、主要な収益源"
    elif segment in ['potential_loyalists', 'promising']:
        return "成長グループ、重点育成対象"
    elif segment in ['at_risk']:
        return "リスクグループ、引き留め戦略 必要"
    elif segment in ['lost']:
        return "解約グループ、呼び戻しコスト 検討"
    else:
        return "さらなる観察 analysis 必要"


def _identify_optimization_opportunities(segment: str) -> List[str]:
    """最適化 機会 特定"""
    opportunities = {
        "champions": ["サービス体験 向上", "製品 クロスセルincrease", "ロイヤルティプログラム build"],
        "loyal_customers": ["製品アップグレード recommendation", "付加価値サービス プロモーション", "口コミマーケティング 奨励"],
        "potential_loyalists": ["コンバージョン促進戦略", "パーソナライズされたコンテンツ", "インタラクティブ体験 最適化"],
        "at_risk": ["迅速な対応メカニズム", "問題診断プロセス", "引き留めインセンティブプラン"],
        "lost": ["呼び戻しコスト 評価", "解約理由 analysis", "再アクティベーション戦略"]
    }
    return opportunities.get(segment, ["特別な最適化計画 策定"])
