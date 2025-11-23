"""
userinsighthandle器 - 统一handleusersegmentation、risk评估、recommendationenhancelogic
消除 base_agent.py and multi_agent_system.py 中 代码重复
"""
from typing import Dict, Any, List, Tuple
from app.core.logging import logger


class UserSegmentConfig:
    """usersegmentationconfigure - 中央化管理所有usersegmentation相关 mapand描述"""
    
    # usersegmentation指令map (for LLM prompts)
    SEGMENT_INSTRUCTIONS = {
        'champions': "这是高价valueuser，请providepremium级别 投资建议",
        'loyal_customers': "这是忠诚客户，请provide稳健 投资策略建议",
        'potential_loyalists': "这是有潜力 user，请provide成长型投资建议",
        'at_risk': "这是有流失risk user，请provide保守但有吸引力 建议",
        'big_spenders': "这是高消费user，请平衡流动性and收益性",
        'promising': "这是有前途 user，建议积极培养",
        'new_customers': "这是newuser，需要耐心引导and教育",
        'new_user': "这是newuser，需要耐心引导and教育",  # 向后兼容
        'lost': "这是流失user，需要重new吸引andactive"
    }
    
    # usersegmentationrecommendationmap (for consensus recommendations)
    SEGMENT_RECOMMENDATIONS = {
        'champions': "作为高价valueuser，recommendation关注高端投asset品and专属service",
        'loyal_customers': "作为忠诚客户，建议保持稳健growth策略，考虑多元化configure",
        'potential_loyalists': "您具有很好 成长潜力，建议逐步增加投资比例",
        'at_risk': "建议重new审视投资策略，make sure符合您 risk承受能力",
        'big_spenders': "基于您 高消费特征，建议平衡流动性andgrowth性投资",
        'promising': "您是很有前途 投资者，建议关注成长性投资opportunity",
        'new_customers': "欢迎您！建议frombase稳健 投资方式begin",
        'new_user': "欢迎您！建议frombase稳健 投资方式begin",  # 向后兼容
        'lost': "欢迎回归！我们为您prepare了特别 重newbegin方案"
    }
    
    # usersegmentation描述map (for assessments)
    SEGMENT_DESCRIPTIONS = {
        'champions': "您是我们 冠军user！拥有优秀 投资table现andheight参and",
        'loyal_customers': "您是忠诚 客户，具有稳定 投资习惯",
        'potential_loyalists': "您展现出良好 投资潜力and学习能力",
        'promising': "您是很有前途 投资者，value得重点培养",
        'new_customers': "欢迎您！我们将为您provide专业 投资指导",
        'new_user': "欢迎您！我们将为您provide专业 投资指导",  # 向后兼容
        'at_risk': "我们note到您可能需要一些帮助，请随时联系我们",
        'big_spenders': "基于您 高价value特征，我们recommendationpersonalized 投资方案",
        'lost': "欢迎回来！我们很高兴重new为您service"
    }
    
    # personalizedrecommendation模板 (整合自 insights_service_optimized.py)
    PERSONALIZED_RECOMMENDATIONS = {
        "champions": [
            "🏆 专属高端投asset品recommendation",
            "💎 VIP客户专享service",
            "🎯 个人投资顾问service"
        ],
        "loyal_customers": [
            "📈 稳健growth投资策略",
            "🎁 忠诚user奖励计划",
            "👥 recommendation朋友获得奖励"
        ],
        "potential_loyalists": [
            "🚀 多元化投资选择",
            "📚 投资教育in容recommendation",
            "💰 小额试水投资opportunity"
        ],
        "at_risk": [
            "🔔 特别关怀计划",
            "💸 专享优惠活动",
            "📞 客服主动关怀"
        ],
        "lost": [
            "🎉 回归欢迎奖励",
            "✨newfeature体验邀请",
            "🆓 零门槛重newbegin"
        ],
        "new_customers": [
            "🌟 new手投资指南",
            "🎓 base投资教育",
            "💡 简化投资建议"
        ],
        "new_user": [  # 向后兼容
            "🌟 new手投资指南",
            "🎓 base投资教育",
            "💡 简化投资建议"
        ],
        "big_spenders": [
            "💼 高价value投资方案",
            "🏦 私人银行service",
            "📊 定制化assetconfigure"
        ],
        "promising": [
            "📈 成长型投资opportunity",
            "🎯 潜力挖掘计划",
            "🚀 进阶投资策略"
        ]
    }


class RiskAssessmentProcessor:
    """risk评估handle器 - 统一handle流失riskandgrowth潜力 评估logic"""
    
    @staticmethod
    def get_churn_risk_instructions(churn_risk: int) -> List[str]:
        """基于流失riskgenerate指令"""
        instructions = []
        if churn_risk > 70:
            instructions.append("⚠️ user流失risk高，请特别noteuser体验and简化operations")
        elif churn_risk > 50:
            instructions.append("user活跃度有下降trend，请provide有吸引力 建议")
        elif churn_risk > 30:
            instructions.append("user参and度一般，需要适当激励")
        return instructions
    
    @staticmethod
    def get_churn_risk_recommendations(churn_risk: int) -> List[str]:
        """基于流失riskgeneraterecommendation"""
        recommendations = []
        if churn_risk > 70:
            recommendations.append("⚠️ 我们将为您provide专属 投资指导and支持service")
        elif churn_risk > 60:
            recommendations.append("⚠️ 建议关注投资体验，如有疑问请随时联系客服")
        elif churn_risk > 40:
            recommendations.append("💡 建议您保持定期关注投资动态，我们会持续为您provide优质service")
        return recommendations
    
    @staticmethod
    def get_growth_potential_instructions(growth_potential: int) -> List[str]:
        """基于growth潜力generate指令"""
        instructions = []
        if growth_potential > 80:
            instructions.append("🚀 user具有高growth潜力，可以recommendation更积极 策略")
        elif growth_potential > 60:
            instructions.append("user有良好 成长space，适度optimize投资configure")
        elif growth_potential > 40:
            instructions.append("user具有一定成长潜力，可以try多样化投资")
        return instructions
    
    @staticmethod
    def get_growth_strategy_recommendation(strategy: str) -> str:
        """基于growth策略getrecommendation"""
        strategy_recommendations = {
            'aggressive_growth': "您适合进取型投资策略，可考虑适度增加riskasset比例",
            'moderate_growth': "建议采用平衡型投资策略，分散投资risk",
            'conservative_growth': "recommendation稳健型投资方式，优first保障本金安全",
            'stability_focused': "建议以稳定性为主，重点关注asset保value"
        }
        return strategy_recommendations.get(strategy, "建议根据个人risk偏好制定投资策略")


class FallbackRecommendationGenerator:
    """downgraderecommendationgenerator - 统一generate基于insight downgraderecommendation"""
    
    @staticmethod
    def generate_agent_level_recommendations(
        agent_name: str, 
        user_segment: str, 
        churn_risk: int, 
        growth_potential: int
    ) -> List[Dict[str, Any]]:
        """generate智能体级别 downgraderecommendation"""
        recommendations = []
        
        # 基于usersegmentation recommendation
        if user_segment == 'champions':
            recommendations.append({
                'title': f'🏆 专属servicerecommendation',
                'description': f'基于您 {agent_name}use情况，recommendationupgrade到VIPservice',
                'potential_gain': 5000.0
            })
        elif user_segment == 'at_risk':
            recommendations.append({
                'title': f'💡 简化operations建议',
                'description': f'我们为您 {agent_name}prepare了更简单 operations方式',
                'potential_gain': 1000.0
            })
        elif user_segment == 'loyal_customers':
            recommendations.append({
                'title': f'🎯 忠诚客户专享',
                'description': f'基于您对{agent_name} 持续use，为您provide专享optimize方案',
                'potential_gain': 3000.0
            })
        else:
            recommendations.append({
                'title': f'📊 optimize建议',
                'description': f'基于您 userprofile，建议关注{agent_name} useoptimize',
                'potential_gain': 2000.0
            })
        
        # 基于riskand潜力 额外recommendation
        if churn_risk > 70:
            recommendations.append({
                'title': '🔔 专属关怀',
                'description': '我们 专业团队将为您provide一对一 投资指导',
                'potential_gain': 0.0
            })
        
        if growth_potential > 70:
            recommendations.append({
                'title': '🚀 成长opportunity',
                'description': f'基于您 高growth潜力，{agent_name}有更多发展space',
                'potential_gain': 8000.0
            })
        
        return recommendations[:2]  # 最多return2个recommendation
    
    @staticmethod
    def generate_system_level_recommendations(
        user_segment: str,
        churn_risk: int, 
        growth_potential: int,
        personalized_recs: List[str] = None
    ) -> List[str]:
        """generatesystem级别 downgraderecommendation"""
        recommendations = []
        
        # 基于segmentation baserecommendation
        segment_base_recs = {
            'champions': [
                "continue保持优秀 投资策略",
                "考虑关注更多高端投资opportunity"
            ],
            'loyal_customers': [
                "保持existing 稳健投资风格",
                "考虑适度 多元化投资"
            ],
            'at_risk': [
                "建议重new审视currentportfolio",
                "如有疑问，欢迎咨询我们 专业团队"
            ],
            'potential_loyalists': [
                "您 投资潜力value得培养",
                "建议逐步扩大投资range"
            ]
        }
        
        if user_segment in segment_base_recs:
            recommendations.extend(segment_base_recs[user_segment])
        else:
            recommendations.append("建议定期关注投资动态，optimizeassetconfigure")
        
        # 基于risk recommendation
        if churn_risk > 70:
            recommendations.append("我们将为您provide专属 投资指导and支持service")
        elif churn_risk > 50:
            recommendations.append("建议保持and我们 密切沟通，及时adjust投资策略")
        
        # 基于growth潜力 recommendation
        if growth_potential > 70:
            recommendations.append("基于您 高growth潜力，建议考虑更积极 投资策略")
        elif growth_potential > 50:
            recommendations.append("您具有良好 成长space，建议适度optimize投资configure")
        
        # addpersonalizedrecommendation
        if personalized_recs:
            recommendations.extend(personalized_recs[:2])
        
        return recommendations if recommendations else ["我们将基于您 具体情况providepersonalized建议"]
    
    @staticmethod
    def generate_personalized_recommendations(insights: Dict[str, Any]) -> List[str]:
        """
        基于insightgeneratepersonalizedrecommendation (整合自 insights_service_optimized.py)
        
        Args:
            insights: includesuserinsight dictionary
        
        Returns:
            personalizedrecommendationlist
        """
        recommendations = []
        
        user_segment = insights.get("user_segment", "unknown")
        churn_risk = insights.get("churn_risk", {}).get("score", 50)
        growth_potential = insights.get("growth_potential", {}).get("score", 50)
        
        # 基于usersegmentation baserecommendation
        if user_segment in UserSegmentConfig.PERSONALIZED_RECOMMENDATIONS:
            recommendations.extend(UserSegmentConfig.PERSONALIZED_RECOMMENDATIONS[user_segment])
        else:
            recommendations.append("🌟 personalized投资建议")
        
        # 基于流失risk 额外recommendation
        if churn_risk > 70:
            recommendations.append("⚠️ 紧急：专属挽留优惠")
        elif churn_risk > 50:
            recommendations.append("📢 活跃度提升计划")
        
        # 基于growth潜力 recommendation
        if growth_potential > 80:
            recommendations.append("🚀 高潜力投资opportunity")
        elif growth_potential > 60:
            recommendations.append("📊 growth策略optimize建议")
        
        return recommendations[:5]  # 最多return5个recommendation


class InsightEnhancementProcessor:
    """insightenhancehandle器 - 统一handlerecommendationenhanceand评估enhancelogic"""
    
    @staticmethod
    def enhance_recommendation_title(
        original_title: str, 
        user_segment: str, 
        growth_potential: int
    ) -> str:
        """enhancerecommendation标题"""
        if user_segment == 'champions':
            return f"🏆 [高价valueuser专属] {original_title}"
        elif user_segment == 'at_risk':
            return f"💡 [特别关怀] {original_title}"
        elif growth_potential > 70:
            return f"🚀 [高潜力] {original_title}"
        else:
            return original_title
    
    @staticmethod
    def adjust_potential_gain(
        original_gain: float, 
        churn_risk: int, 
        growth_potential: int
    ) -> float:
        """adjust潜在收益"""
        if churn_risk > 70:
            # 高riskuser：适度降低收益预期
            return original_gain * 0.8
        elif growth_potential > 70:
            # 高潜力user：适度提高收益预期
            return original_gain * 1.2
        else:
            return original_gain
    
    @staticmethod
    def build_enhanced_context_string(
        enhanced_context: Dict[str, Any], 
        feedback_history_str: str
    ) -> str:
        """构建enhance context字符串"""
        user_segment = enhanced_context.get('user_segment', 'unknown')
        user_scores = enhanced_context.get('user_scores', {})
        churn_risk = enhanced_context.get('churn_risk', {})
        growth_potential = enhanced_context.get('growth_potential', {})
        
        context_parts = [
            "=== userdepthinsight ===",
            f"usersegmentation: {user_segment}",
            f"user评分: 价value={user_scores.get('value', 0)}, 活跃度={user_scores.get('activity', 0)}, 忠诚度={user_scores.get('loyalty', 0)}",
            f"流失risk: {churn_risk.get('score', 0)}分 ({churn_risk.get('category', 'unknown')})",
            f"growth潜力: {growth_potential.get('score', 0)}分 ({growth_potential.get('strategy', 'moderate_growth')})",
        ]
        
        # addrisk预警
        risk_score = churn_risk.get('score', 0)
        if risk_score > 70:
            context_parts.append("⚠️ note：该userexists高流失risk，需要特别关注")
        
        # addgrowthopportunity
        growth_score = growth_potential.get('score', 0)
        if growth_score > 70:
            context_parts.append("🚀 opportunity：该user具有高growth潜力，可recommendation进取型策略")
        
        # add市场trend
        market_trends = enhanced_context.get('market_trends', {})
        if market_trends.get('trending_categories'):
            trending = market_trends['trending_categories'][:3]
            context_parts.append(f"📈 current热门class别: {trending}")
        
        # addpersonalizedrecommendation
        personalized_recs = enhanced_context.get('personalized_recommendations', [])
        if personalized_recs:
            context_parts.append(f"🎯 personalized建议: {', '.join(personalized_recs[:3])}")
        
        context_parts.extend([
            "",
            "=== historyfeedback ===",
            feedback_history_str,
            "",
            "请基于以上userinsightandhistoryfeedback，provide更精准 personalized投资建议。"
        ])
        
        return "\n".join(context_parts)


class MarketTrendsProcessor:
    """市场trendhandle器 - 统一handle市场trendanalysislogic (整合自 insights_service_optimized.py)"""
    
    @staticmethod
    def analyze_market_sentiment(rising_trends: List[Dict[str, Any]]) -> str:
        """analysis市场情绪"""
        if not rising_trends:
            return "neutral"
        
        rising_count = len([t for t in rising_trends if t.get('price_trend') == 'rising'])
        
        if rising_count >= 5:
            return "bullish"
        elif rising_count >= 2:
            return "optimistic"
        else:
            return "neutral"
    
    @staticmethod
    def format_market_context(cached_data: Dict[str, Any]) -> Dict[str, Any]:
        """format市场contextdata"""
        if not cached_data:
            return {"trending_categories": [], "market_sentiment": "neutral"}
        
        rising_trends = cached_data.get("rising_trends", [])
        return {
            "trending_categories": cached_data.get("hot_categories", []),
            "rising_trends": rising_trends[:5],  # 前5个上升trend
            "market_sentiment": MarketTrendsProcessor.analyze_market_sentiment(rising_trends),
            "data_freshness": cached_data.get("updated_at", "unknown")
        }


class FallbackInsightsGenerator:
    """downgradeinsightgenerator - 统一generatedataunavailable时 downgradeinsight (整合自 insights_service_optimized.py)"""
    
    @staticmethod
    def generate_fallback_insights(user_id: str) -> Dict[str, Any]:
        """getdowngradeinsight（当cacheunavailable时）"""
        from datetime import datetime
        
        return {
            "user_id": user_id,
            "generated_at": datetime.now().isoformat(),
            "user_segment": "new_user",
            "scores": {"value": 0, "activity": 0, "loyalty": 0, "overall": 0},
            "churn_risk": {"score": 30, "category": "active"},
            "growth_potential": {"score": 50, "strategy": "moderate_growth"},
            "asset_allocation": {"current_strategy": "unknown", "recommended_strategy": "balanced"},
            "market_context": {"trending_categories": []},
            "personalized_recommendations": [
                "🌟 欢迎use投资顾问system", 
                "📊 建议完善个人资料"
            ],
            "data_quality": {
                "freshness": "downgrademode", 
                "confidence": 0.0, 
                "data_available": False
            },
            "cache_status": "miss",
            "response_time_ms": 5.0
        }
