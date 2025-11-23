import asyncio
from typing import Dict, List, Any, Optional
from app.models.assets import UserPortfolio, AssetType
from app.models.recommendations import MultiAgentResponse, AgentAnalysis, RecommendationDetail
from app.agents.asset_agents import (
    PointsAgent, EarningsAgent, ItemsAgent, 
    GigaAgent, StablecoinAgent, GeneralPortfolioAnalyzer
)
from app.agents.base_agent import BaseAgent
from app.core.logging import logger
from app.services.firestore.firestore_primary_service import get_firestore_primary_service
from pydantic import ValidationError

class MultiAgentSystem:
    """マルチエージェントシステム - 5つの資産タイプ別エージェントを管理"""
    
    def __init__(self):
        self.agents: Dict[AssetType, BaseAgent] = {
            AssetType.POINTS: PointsAgent(),
            AssetType.EARNINGS: EarningsAgent(),
            AssetType.ITEMS: ItemsAgent(),
            AssetType.GIGA: GigaAgent(),
            AssetType.STABLECOIN: StablecoinAgent(),
        }
        self.general_analyzer = GeneralPortfolioAnalyzer()
        self.firestore_service = get_firestore_primary_service()

    async def analyze_portfolio(self, portfolio: UserPortfolio) -> MultiAgentResponse:
        """
        全エージェントによるポートフォリオ分析を実行
        """
        feedback_history = await self.firestore_service.get_user_feedback_history(portfolio.user_id)
        feedback_history_str = self.general_analyzer._format_feedback_for_prompt(feedback_history)

        agent_tasks = []
        for asset in portfolio.assets:
            agent = self.agents.get(asset.asset_type)
            if agent:
                agent_tasks.append(agent.analyze(portfolio, feedback_history_str))

        results = await asyncio.gather(*agent_tasks, return_exceptions=True)

        agent_analyses = []
        for i, result in enumerate(results):
            agent = list(self.agents.values())[i]
            if isinstance(result, tuple):
                analysis_summary, recommendations = result

                processed_recommendations = []
                for rec in recommendations:
                    try:
                        # Sanitize potential_gain before validation
                        gain = rec.get("potential_gain")
                        if not isinstance(gain, (int, float)):
                            logger.warning(
                                f"Agent {agent.agent_name} provided non-numeric potential_gain: '{gain}'. Defaulting to 0.0."
                            )
                            rec["potential_gain"] = 0.0
                        
                        processed_recommendations.append(RecommendationDetail(**rec))
                    except ValidationError as e:
                        logger.error(
                            f"Pydantic validation error for recommendation from agent {agent.agent_name}: {e}. Data: {rec}"
                        )
                        continue

                if not analysis_summary and not processed_recommendations:
                    logger.warning(
                        f"Agent {agent.agent_name} produced no valid analysis or recommendations."
                    )
                    continue

                agent_analyses.append(
                    AgentAnalysis(
                        agent_name=agent.agent_name,
                        asset_type=agent.asset_type,
                        findings=analysis_summary,
                        recommendations=processed_recommendations,
                    )
                )
            elif isinstance(result, Exception):
                logger.error(f"Agent {agent.agent_name} failed: {result}")

        # Fallback logic if no agents were run or all failed
        if not agent_analyses:
            assessment = "分析可能な資産がポートフォリオに見つからないか、分析中にエラーが発生しました。資産状況をご確認ください。"
            return MultiAgentResponse(
                user_id=portfolio.user_id,
                analyses=[],
                consensus_recommendations=["現在、具体的な推奨事項はありません。"],
                overall_assessment=assessment
            )

        # Restore helper functions to build the correct response model
        consensus = self._generate_consensus(agent_analyses)
        assessment = self._generate_overall_assessment(portfolio, agent_analyses)

        return MultiAgentResponse(
            user_id=portfolio.user_id,
            analyses=agent_analyses,
            consensus_recommendations=consensus,
            overall_assessment=assessment
        )

    async def analyze_portfolio_with_insights(self, portfolio: UserPortfolio, enhanced_context: Dict[str, Any]) -> MultiAgentResponse:
        """
        インテリジェントポートフォリオ分析 - BigQueryの深い洞察を統合
        
        Args:
            portfolio: ユーザーポートフォリオ
            enhanced_context: ユーザーセグメント、リスク評価、成長ポテンシャルなどを含む強化された分析コンテキスト
        
        Returns:
            強化されたマルチエージェント分析結果
        """
        logger.info(f"🧠 インテリジェント分析を実行: user_id={portfolio.user_id}, segment={enhanced_context.get('user_segment')}")
        
        # フィードバック履歴を取得
        feedback_history = await self.firestore_service.get_user_feedback_history(portfolio.user_id)
        feedback_history_str = self.general_analyzer._format_feedback_for_prompt(feedback_history)
        
        # 強化されたコンテキスト情報を構築
        enhanced_feedback = self._build_enhanced_context_string(enhanced_context, feedback_history_str)
        
        agent_tasks = []
        for asset in portfolio.assets:
            agent = self.agents.get(asset.asset_type)
            if agent:
                # 強化されたコンテキストを使用して分析
                agent_tasks.append(agent.analyze_with_insights(portfolio, enhanced_feedback, enhanced_context))
        
        results = await asyncio.gather(*agent_tasks, return_exceptions=True)
        
        agent_analyses = []
        for i, result in enumerate(results):
            agent = list(self.agents.values())[i]
            if isinstance(result, tuple):
                analysis_summary, recommendations = result
                
                processed_recommendations = []
                for rec in recommendations:
                    try:
                        # potential_gainデータをクリーンアップ
                        gain = rec.get("potential_gain")
                        if not isinstance(gain, (int, float)):
                            logger.warning(f"エージェント {agent.agent_name} が非数値のpotential_gainを提供: '{gain}'. デフォルトは0.0.")
                            rec["potential_gain"] = 0.0
                        
                        processed_recommendations.append(RecommendationDetail(**rec))
                    except ValidationError as e:
                        logger.error(f"エージェント {agent.agent_name} の推薦で検証エラー: {e}. Data: {rec}")
                        continue
                
                if not analysis_summary and not processed_recommendations:
                    logger.warning(f"エージェント {agent.agent_name} は有効な分析または推薦を生成しませんでした.")
                    continue
                
                agent_analyses.append(
                    AgentAnalysis(
                        agent_name=agent.agent_name,
                        asset_type=agent.asset_type,
                        findings=analysis_summary,
                        recommendations=processed_recommendations,
                    )
                )
            elif isinstance(result, Exception):
                logger.error(f"エージェント {agent.agent_name} の分析が失敗: {result}")
        
        # 成功した分析がない場合、フォールバック応答を返す
        if not agent_analyses:
            assessment = self._generate_fallback_assessment_with_insights(portfolio, enhanced_context)
            return MultiAgentResponse(
                user_id=portfolio.user_id,
                analyses=[],
                consensus_recommendations=self._generate_insights_based_recommendations(enhanced_context),
                overall_assessment=assessment
            )
        
        # 強化されたコンセンサス推薦と評価を生成
        consensus = self._generate_enhanced_consensus(agent_analyses, enhanced_context)
        assessment = self._generate_enhanced_assessment(portfolio, agent_analyses, enhanced_context)
        
        return MultiAgentResponse(
            user_id=portfolio.user_id,
            analyses=agent_analyses,
            consensus_recommendations=consensus,
            overall_assessment=assessment
        )

    async def analyze_general_portfolio(self, portfolio: UserPortfolio, feedback_history: List[Dict[str, Any]]) -> str:
        """
        Analyzes the entire portfolio to return a natural language summary.
        This is a helper for a specific endpoint and reuses the general analyzer.
        """
        feedback_history_str = self.general_analyzer._format_feedback_for_prompt(feedback_history)
        analysis_summary, _ = await self.general_analyzer.analyze(portfolio, feedback_history_str)
        return analysis_summary

    def _generate_consensus(self, analyses: List[AgentAnalysis]) -> List[str]:
        # Logic to generate consensus recommendations
        if not analyses:
            return ["具体的な分析結果がないため、共通の推奨事項はありません。"]
        # Dummy logic for now
        return ["資産ポートフォリオの定期的な見直しと最適化を推奨します。"]

    def _generate_overall_assessment(self, portfolio: UserPortfolio, analyses: List[AgentAnalysis]) -> str:
        # Logic to generate an overall assessment
        total_assets = portfolio.total_assets
        analysis_count = len(analyses)
        if analysis_count == 0:
            return "利用可能な資産の分析に失敗したため、総合評価は提供できません。"
        
        return f"総資産額¥{total_assets:,.0f}に対し、{analysis_count}種類の資産について分析しました。安定性と成長性のバランスを考慮した運用が重要です。"
    
    # ================ 強化分析のためのヘルパーメソッド ================
    
    def _build_enhanced_context_string(self, enhanced_context: Dict[str, Any], feedback_history_str: str) -> str:
        """AIエージェントが使用する強化されたコンテキスト文字列を構築する"""
        user_segment = enhanced_context.get('user_segment', 'unknown')
        user_scores = enhanced_context.get('user_scores', {})
        churn_risk = enhanced_context.get('churn_risk', {})
        growth_potential = enhanced_context.get('growth_potential', {})
        
        context_parts = [
            "=== ユーザー詳細インサイト ===",
            f"ユーザーセグメント: {user_segment}",
            f"ユーザースコア: 価値={user_scores.get('value', 0)}, アクティビティ={user_scores.get('activity', 0)}, 忠誠度={user_scores.get('loyalty', 0)}",
            f"離反リスク: {churn_risk.get('score', 0)}点 ({churn_risk.get('category', 'unknown')})",
            f"成長ポテンシャル: {growth_potential.get('score', 0)}点 ({growth_potential.get('strategy', 'moderate_growth')})",
        ]
        
        # リスク警告を追加
        if churn_risk.get('score', 0) > 70:
            context_parts.append("⚠️ 注意：このユーザーは離反リスクが高いため、特別な注意が必要です")
        
        # 成長機会を追加
        if growth_potential.get('score', 0) > 70:
            context_parts.append("🚀 機会：このユーザーは高い成長ポテンシャルを持っており、積極的な戦略を推奨できます")
        
        # 市場トレンドを追加
        market_trends = enhanced_context.get('market_trends', {})
        if market_trends.get('trending_categories'):
            trending = market_trends['trending_categories'][:3]
            context_parts.append(f"📈 現在の人気カテゴリ: {trending}")
        
        # パーソナライズされた推薦を追加
        personalized_recs = enhanced_context.get('personalized_recommendations', [])
        if personalized_recs:
            context_parts.append(f"🎯 パーソナライズされた提案: {', '.join(personalized_recs[:3])}")
        
        context_parts.extend([
            "",
            "=== 過去のフィードバック ===",
            feedback_history_str,
            "",
            "上記のユーザーインサイトと過去のフィードバックに基づき、より正確でパーソナライズされた投資アドバイスを提供してください。"
        ])
        
        return "\n".join(context_parts)
    
    def _generate_enhanced_consensus(self, analyses: List[AgentAnalysis], enhanced_context: Dict[str, Any]) -> List[str]:
        """強化されたコンセンサス推薦を生成する"""
        if not analyses:
            return self._generate_insights_based_recommendations(enhanced_context)
        
        consensus = []
        
        # 基本的なコンセンサス推薦
        consensus.append("詳細なユーザー分析に基づき、定期的な資産配分の最適化を推奨します")
        
        # ユーザーセグメントに基づく推薦
        user_segment = enhanced_context.get('user_segment', 'unknown')
        segment_recommendations = {
            'champions': "高価値ユーザーとして、ハイエンド投資商品や専用サービスに注目することをお勧めします",
            'loyal_customers': "忠実な顧客として、安定した成長戦略を維持し、分散投資を検討することをお勧めします",
            'potential_loyalists': "優れた成長ポテンシャルをお持ちですので、徐々に投資比率を高めることをお勧めします",
            'at_risk': "現在の投資戦略を見直し、リスク許容度に合っているか確認することをお勧めします",
            'big_spenders': "高い消費特性に基づき、流動性と成長性のバランスの取れた投資をお勧めします"
        }
        
        if user_segment in segment_recommendations:
            consensus.append(segment_recommendations[user_segment])
        
        # リスク評価に基づく提案
        churn_risk = enhanced_context.get('churn_risk', {}).get('score', 0)
        if churn_risk > 60:
            consensus.append("⚠️ 投資体験にご注意いただき、ご不明な点があればいつでもカスタマーサービスにご連絡ください")
        
        # 成長ポテンシャルに基づく提案
        growth_strategy = enhanced_context.get('growth_potential', {}).get('strategy', 'moderate_growth')
        strategy_recommendations = {
            'aggressive_growth': "積極的な投資戦略が適しており、リスク資産の比率を適度に増やすことを検討できます",
            'moderate_growth': "バランスの取れた投資戦略を採用し、投資リスクを分散させることをお勧めします",
            'conservative_growth': "安定した投資方法を推奨し、元本の安全を優先します",
            'stability_focused': "安定性を主とし、資産価値の維持に重点を置くことをお勧めします"
        }
        
        if growth_strategy in strategy_recommendations:
            consensus.append(strategy_recommendations[growth_strategy])
        
        return consensus
    
    def _generate_enhanced_assessment(self, portfolio: UserPortfolio, analyses: List[AgentAnalysis], enhanced_context: Dict[str, Any]) -> str:
        """強化された全体評価を生成する"""
        total_assets = portfolio.total_assets
        analysis_count = len(analyses)
        user_segment = enhanced_context.get('user_segment', 'unknown')
        churn_risk = enhanced_context.get('churn_risk', {}).get('score', 0)
        growth_potential = enhanced_context.get('growth_potential', {}).get('score', 0)
        
        assessment_parts = []
        
        # 基本評価
        assessment_parts.append(f"📊 総資産額¥{total_assets:,.0f}、{analysis_count}種類の資産タイプを分析済み")
        
        # ユーザーセグメント評価
        segment_descriptions = {
            'champions': "あなたは私たちのチャンピオンユーザーです！優れた投資実績と高いエンゲージメントをお持ちです",
            'loyal_customers': "あなたは忠実な顧客であり、安定した投資習慣をお持ちです",
            'potential_loyalists': "あなたは良好な投資ポテンシャルと学習能力を示しています",
            'promising': "あなたは将来有望な投資家であり、重点的に育成する価値があります",
            'new_customers': "ようこそ！専門的な投資指導を提供いたします",
            'at_risk': "サポートが必要な可能性があることを認識しております。いつでもご連絡ください",
            'big_spenders': "高い価値特性に基づき、パーソナライズされた投資プランをお勧めします"
        }
        
        if user_segment in segment_descriptions:
            assessment_parts.append(f"👤 {segment_descriptions[user_segment]}")
        
        # リスク警告
        if churn_risk > 70:
            assessment_parts.append("⚠️ 最近のアクティビティが低下しているようです。投資に関するご質問があれば、専門チームがいつでもサポートいたします")
        elif churn_risk > 50:
            assessment_parts.append("💡 定期的に投資動向に注意を払うことをお勧めします。引き続き質の高いサービスを提供いたします")
        
        # 成長機会
        if growth_potential > 80:
            assessment_parts.append("🚀 高い投資成長ポテンシャルをお持ちです。より積極的な投資戦略を検討することをお勧めします")
        elif growth_potential > 60:
            assessment_parts.append("📈 投資の成長余地は良好です。資産配分を適度に最適化することができます")
        
        # データ品質に関する注意
        data_confidence = enhanced_context.get('data_confidence', 0.5)
        if data_confidence < 0.7:
            assessment_parts.append("📊 より正確な分析を提供できるよう、個人の投資情報をさらに充実させることをお勧めします")
        
        assessment_parts.append("🎯 あなたの個人的な特性と市場トレンドに基づき、上記の分析はあなたのためにカスタマイズされています")
        
        return "\n\n".join(assessment_parts)
    
    def _generate_fallback_assessment_with_insights(self, portfolio: UserPortfolio, enhanced_context: Dict[str, Any]) -> str:
        """洞察に基づいたフォールバック評価を生成する"""
        user_segment = enhanced_context.get('user_segment', 'unknown')
        churn_risk = enhanced_context.get('churn_risk', {}).get('score', 0)
        
        assessment_parts = [
            f"📊 総資産額¥{portfolio.total_assets:,.0f}",
            "詳細な分析は現在利用できませんが、あなたのユーザープロファイルに基づくと："
        ]
        
        if user_segment != 'unknown':
            assessment_parts.append(f"👤 あなたは{user_segment}ユーザーグループに属しています")
        
        if churn_risk > 70:
            assessment_parts.append("⚠️ 追加の注意とサポートが必要な可能性があることを認識しています")
        
        assessment_parts.append("🎯 引き続き、パーソナライズされた投資アドバイスと質の高いサービスを提供いたします")
        
        return "\n\n".join(assessment_parts)
    
    def _generate_insights_based_recommendations(self, enhanced_context: Dict[str, Any]) -> List[str]:
        """洞察に基づく推薦を生成する（エージェント分析失敗時のフォールバックプラン）"""
        recommendations = []
        
        user_segment = enhanced_context.get('user_segment', 'unknown')
        churn_risk = enhanced_context.get('churn_risk', {}).get('score', 0)
        growth_potential = enhanced_context.get('growth_potential', {}).get('score', 0)
        
        # セグメントに基づく基本推薦
        if user_segment == 'champions':
            recommendations.extend([
                "優れた投資戦略を引き続き維持してください",
                "より多くのハイエンド投資機会に注目することを検討してください"
            ])
        elif user_segment == 'at_risk':
            recommendations.extend([
                "現在の投資ポートフォリオを再検討することをお勧めします",
                "ご不明な点があれば、専門チームにご相談ください"
            ])
        else:
            recommendations.append("定期的に投資動向に注意を払い、資産配分を最適化することをお勧めします")
        
        # リスクに基づく推薦
        if churn_risk > 70:
            recommendations.append("あなた専用の投資指導とサポートサービスを提供いたします")
        
        # 成長ポテンシャルに基づく推薦
        if growth_potential > 70:
            recommendations.append("高い成長ポテンシャルに基づき、より積極的な投資戦略を検討することをお勧めします")
        
        # パーソナライズされた推薦
        personalized_recs = enhanced_context.get('personalized_recommendations', [])
        recommendations.extend(personalized_recs[:2])  # 最初の2つのパーソナライズされた推薦を追加
        
        return recommendations if recommendations else ["あなたの具体的な状況に基づき、パーソナライズされた提案を提供いたします"]

multi_agent_system = MultiAgentSystem()