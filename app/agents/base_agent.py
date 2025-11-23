from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, Union, List, Tuple
from app.models.assets import UserPortfolio, AssetType
from app.models.recommendations import AgentAnalysis, RecommendationDetail
from app.services.llm.openai_service import OpenAIService
from app.core.logging import logger
import re
import json

class BaseAgent(ABC):
    """資産analysisエージェントの基底クラス"""
    
    def __init__(self, agent_name: str, asset_type: Union[AssetType, str]):
        self.agent_name = agent_name
        self.asset_type = asset_type
        self.llm_service = OpenAIService()
    
    async def analyze(
        self, portfolio: UserPortfolio, feedback_history: str = ""
    ) -> Tuple[str, List[Dict[str, Any]]]:
        """
        Analyzes the user's asset data using an LLM and returns findings and recommendations.
        This is a concrete implementation that subclasses will inherit.
        """
        try:
            user_data = await self._get_asset_data(portfolio)
            if user_data is None:
                logger.warning(f"Agent {self.agent_name} found no data for asset type {self.asset_type.value} in the portfolio.")
                return f"{self.agent_name}のデータが見つかりませんでした。", []

            prompt = self._build_prompt(user_data, feedback_history)
            
            response_text = await self.llm_service.generate_completion(
                prompt, max_tokens=1024, temperature=0.7
            )
            
            analysis_summary, recommendations = self._extract_recommendations(response_text)
            
            return analysis_summary, recommendations

        except Exception as e:
            logger.error(f"Agent {self.agent_name} failed: {e}")
            # Raise the exception to be caught by the multi-agent system
            raise
    
    async def analyze_with_insights(
        self, portfolio: UserPortfolio, enhanced_feedback: str, enhanced_context: Dict[str, Any]
    ) -> Tuple[str, List[Dict[str, Any]]]:
        """
        BigQueryの深いinsightを活用して、強化されたanalysisを実行します。
        
        Args:
            portfolio: ユーザーのポートフォリオ
            enhanced_feedback: ユーザーのinsightを含む強化されたフィードバック文字column
            enhanced_context: 構造化された強化コンテキストデータ
        
        Returns:
            analysisの要約と推奨事項のリストのタプル
        """
        try:
            user_data = await self._get_asset_data(portfolio)
            if user_data is None:
                logger.warning(f"エージェント {self.agent_name} はポートフォリオ内でアセットタイプ {self.asset_type.value} のデータを見つけられませんでした。")
                return f"{self.agent_name}のデータはありませんが、ユーザーのinsightに基づいた推奨事項を提供します。", self._generate_fallback_recommendations_with_insights(enhanced_context)

            # 強化されたコンテキストをuseしてプロンプトを構築
            prompt = self._build_enhanced_prompt(user_data, enhanced_feedback, enhanced_context)
            
            response_text = await self.llm_service.generate_completion(
                prompt, max_tokens=1200, temperature=0.7  # コンテキストを増やすため、max_tokensを少し増加
            )
            
            analysis_summary, recommendations = self._extract_recommendations(response_text)
            
            # 後処理：ユーザーのinsightに基づいて推奨事項を調整
            enhanced_recommendations = self._enhance_recommendations_with_insights(recommendations, enhanced_context)
            
            return analysis_summary, enhanced_recommendations

        except Exception as e:
            logger.error(f"エージェント {self.agent_name} の強化analysisが失敗しました: {e}")
            # insightに基づいたフォールバックanalysisを提供
            return self._generate_insights_fallback_analysis(enhanced_context)
    
    async def regenerate_recommendation(
        self, asset_data: Any, rejection_reason: str, feedback_history: str
    ) -> Optional[Dict[str, Any]]:
        """
        ユーザーのフィードバックに基づき、単一の新しい推奨事項を再generateします。
        """
        logger.info(f"ユーザーのために推奨事項を再generateしています...")
        
        prompt = self._build_regeneration_prompt(asset_data, rejection_reason, feedback_history)
        
        response = await self.llm_service.generate_completion(
            prompt,
            max_tokens=500,
            temperature=0.9,  # Increase temperature for more creative suggestions
        )

        try:
            # Extracts a single JSON object from the response, even if it's in a markdown block
            json_match = re.search(r"\{.*\}", response, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
                data = json.loads(json_str)
                logger.info(f"Successfully regenerated recommendation for agent {self.agent_name}")
                return data
            
            logger.warning(f"No JSON found in regeneration response for {self.agent_name}")
            return None
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse regenerated recommendation JSON for {self.agent_name}: {e}")
            return None

    @abstractmethod
    def _build_prompt(self, user_data: Any, feedback_history: str = "") -> str:
        """各エージェント固有のプロンプトを構築します。"""
        raise NotImplementedError

    def _build_regeneration_prompt(
        self, user_data: Any, rejection_reason: str, feedback_history: str
    ) -> str:
        """
        LLMに新しい推奨事項をgenerateさせるためのプロンプトを構築します。
        """
        def json_serializer(obj):
            """JSONシリアライズ時にdatetimeなどシリアライズ不能なオブジェクトを処理する"""
            if hasattr(obj, 'isoformat'):
                return obj.isoformat()
            return str(obj)
        
        try:
            if hasattr(user_data, 'dict'):
                user_data_str = json.dumps(user_data.dict(), indent=2, ensure_ascii=False, default=json_serializer)
            else:
                user_data_str = json.dumps(user_data, indent=2, ensure_ascii=False, default=json_serializer)
        except Exception as e:
            logger.warning(f"Failed to serialize user_data to JSON: {e}, using string representation")
            user_data_str = str(user_data)

        prompt = f"""
        あなたは経験豊富な金融アドバイザーです。ユーザーの資産状況と過去のフィードバックに基づき、具体的で実行可能な単一の新しい推奨事項を提案してください。

        # ユーザーの資産状況 ({self.asset_type.value})
        ```json
        {user_data_str}
        ```

        # ユーザーが拒否した直前の提案理由
        - {rejection_reason}

        # 過去のフィードバック履歴
        {feedback_history if feedback_history else "なし"}

        # 指示
        1.  上記の情報、特に「拒否した直前の提案理由」を最優先で考慮してください。
        2.  同じような提案や、拒否理由に合致する提案は絶対に避けてください。
        3.  全く異なる角度からの、創造的で新しい提案を一つだけgenerateしてください。
        4.  回答は、以下のJSON形式のみで出力してください。説明文やprependきは不要です。

        # 出力形式 (JSON)
        {{
            "title": "新しい推奨事項の簡潔なタイトル",
            "description": "ユーザーが取るべき具体的な新しい行動を詳細に説明します。",
            "potential_gain": "見込み利益（日本円での数値のみ。文字columnは不可）",
            "risk_level": "リスクレベル（「低」「中」「高」のいずれか）"
        }}
        """
        return prompt

    def _format_feedback_for_prompt(self, feedback_history: List[Dict[str, Any]]) -> str:
        """ユーザーのフィードバック履歴をプロンプト用に整形する"""
        if not feedback_history:
            return "これまでユーザーからの具体的なフィードバックはありません。"

        formatted_feedback = ""
        for feedback in feedback_history:
            if feedback['status'] == 'rejected':
                reason = feedback.get('rejection_reason', '理由不明')
                custom_feedback = feedback.get('rejection_feedback', '')
                formatted_feedback += f"- 拒否された提案: 理由「{reason}」"
                if custom_feedback:
                    formatted_feedback += f"、コメント「{custom_feedback}」"
                formatted_feedback += "\n"
        
        if not formatted_feedback:
            return "これまでユーザーからの拒否フィードバックはありません。"
            
        return "ユーザーは過去に以下の理由で提案を拒否しました。これらの傾向を考慮し、同様の提案を避けてください。:\n" + formatted_feedback

    def _extract_findings(self, response: str) -> str:
        """レスポンスから発見事項を抽出"""
        # 【現状analysisと総合的なアドバイス】セクションの内容を抽出
        match = re.search(r"【現状analysisと総合的なアドバイス】\s*(.*?)\s*【具体的な改善提案】", response, re.DOTALL)
        if match:
            return match.group(1).strip()
        
        # フォールバックとして古い形式も試す
        findings = []
        lines = response.split('\n')
        in_findings_section = False
        for line in lines:
            line = line.strip()
            if '【' in line and 'analysis' in line:
                in_findings_section = True
                continue
            elif '【' in line and '提案' in line:
                in_findings_section = False
                break
            elif in_findings_section and line and not line.startswith('【'):
                findings.append(line)
        
        return "\n".join(findings)

    def _extract_recommendations(self, response: str) -> Tuple[str, List[Dict[str, Any]]]:
        """
        LLMのレスポンスからanalysis概要と推奨事項のリストを抽出します。
        Markdownコードブロックで囲まれている場合でもJSONを抽出できるように堅牢化されています。
        """
        try:
            # Use regex to find the JSON part, even if it's inside a markdown block
            json_match = re.search(r"\{.*\}", response, re.DOTALL)
            if not json_match:
                logger.warning(f"レスポンスからJSON部分が見つかりませんでした: {response}")
                return "analysis結果の取得に失敗しました。", []
            
            json_str = json_match.group(0)
            data = json.loads(json_str)
            
            analysis_summary = data.get("analysis", "analysis概要がありません。")
            recommendations = data.get("recommendations", [])
            
            if not isinstance(recommendations, list):
                logger.warning(f"抽出された 'recommendations' がリストではありません: {recommendations}")
                recommendations = []

            return analysis_summary, recommendations
        except json.JSONDecodeError:
            logger.error(f"JSONparseエラーが発生しました。レスポンス: {response}")
            return "analysis結果のフォーマットが不正です。", []
        except Exception as e:
            logger.error(f"推奨事項の抽出中に予期せぬエラー: {e}")
            return "analysis中に予期せぬエラーが発生しました。", []
    
    @abstractmethod
    async def _get_asset_data(self, portfolio: UserPortfolio) -> Optional[Any]:
        """ポートフォリオから担当資産のデータを取得します。"""
        raise NotImplementedError
    
    def _build_enhanced_prompt(self, user_data: Any, enhanced_feedback: str, enhanced_context: Dict[str, Any]) -> str:
        """
        ユーザーのinsightを統合した、強化されたanalysisプロンプトを構築します。
        
        サブクラスはこのメソッドをオーバーライドして、より専門的なプロンプト構築ロジックを提供できます。
        """
        # 基本プロンプト（既存のメソッドを呼び出し）
        base_prompt = self._build_prompt(user_data, enhanced_feedback)
        
        # 強化された指示をappend
        user_segment = enhanced_context.get('user_segment', 'unknown')
        churn_risk = enhanced_context.get('churn_risk', {}).get('score', 0)
        growth_potential = enhanced_context.get('growth_potential', {}).get('score', 0)
        
        enhanced_instructions = []
        
        # ユーザーセグメントに基づく指示
        segment_instructions = {
            'champions': "これは高価値ユーザーです。プレミアムレベルの投資アドバイスを提供してください。",
            'loyal_customers': "これは忠実な顧客です。安定した投資戦略を提案してください。",
            'potential_loyalists': "これはポテンシャルのあるユーザーです。成長型の投資アドバイスを提案してください。",
            'at_risk': "これは離反リスクのあるユーザーです。保守的かつ魅力的な提案をしてください。",
            'big_spenders': "これは高消費ユーザーです。流動性と収益性のバランスを取ってください。"
        }
        
        if user_segment in segment_instructions:
            enhanced_instructions.append(segment_instructions[user_segment])
        
        # リスクに基づく指示
        if churn_risk > 70:
            enhanced_instructions.append("⚠️ ユーザーの離反リスクが高いです。ユーザー体験と操作の簡素化に特にnoteしてください。")
        elif churn_risk > 50:
            enhanced_instructions.append("ユーザーのアクティビティに低下傾向が見られます。魅力的な提案をしてください。")
        
        # 成長ポテンシャルに基づく指示
        if growth_potential > 80:
            enhanced_instructions.append("🚀 ユーザーは高い成長ポテンシャルを持っています。より積極的な戦略を推奨できます。")
        elif growth_potential > 60:
            enhanced_instructions.append("ユーザーには良好な成長の余地があります。投資配分を適度に最適化してください。")
        
        # 強化されたプロンプトを結合
        if enhanced_instructions:
            enhanced_prompt = base_prompt + "\n\n=== 特別な指示 ===\n" + "\n".join(enhanced_instructions)
            enhanced_prompt += "\n\n上記のユーザー特性に基づいて、analysisと推奨事項を調整してください。"
        else:
            enhanced_prompt = base_prompt
        
        return enhanced_prompt
    
    def _enhance_recommendations_with_insights(self, recommendations: List[Dict[str, Any]], enhanced_context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        ユーザーのinsightに基づいて推奨事項の内容を強化します。
        """
        if not recommendations:
            return self._generate_fallback_recommendations_with_insights(enhanced_context)
        
        enhanced_recs = []
        user_segment = enhanced_context.get('user_segment', 'unknown')
        churn_risk = enhanced_context.get('churn_risk', {}).get('score', 0)
        growth_potential = enhanced_context.get('growth_potential', {}).get('score', 0)
        
        for rec in recommendations:
            enhanced_rec = rec.copy()
            
            # 推奨事項のタイトルをパーソナライズするために調整
            original_title = rec.get('title', '')
            if user_segment == 'champions':
                enhanced_rec['title'] = f"🏆 [高価値ユーザー限定] {original_title}"
            elif user_segment == 'at_risk':
                enhanced_rec['title'] = f"💡 [特別ケア] {original_title}"
            elif growth_potential > 70:
                enhanced_rec['title'] = f"🚀 [高ポテンシャル] {original_title}"
            
            # 潜在的な利益を調整（ユーザーのリスク許容度に基づく）
            if 'potential_gain' in enhanced_rec and enhanced_rec['potential_gain'] > 0:
                original_gain = enhanced_rec['potential_gain']
                
                # 高リスクユーザー：利益予測を適度に引き下げる
                if churn_risk > 70:
                    enhanced_rec['potential_gain'] = original_gain * 0.8
                # 高ポテンシャルユーザー：利益予測を適度に引き上げる
                elif growth_potential > 70:
                    enhanced_rec['potential_gain'] = original_gain * 1.2
            
            enhanced_recs.append(enhanced_rec)
        
        return enhanced_recs
    
    def _generate_fallback_recommendations_with_insights(self, enhanced_context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        ユーザーのinsightに基づいてフォールバック推奨事項をgenerateします（資産データが利用できない場合）。
        """
        user_segment = enhanced_context.get('user_segment', 'unknown')
        churn_risk = enhanced_context.get('churn_risk', {}).get('score', 0)
        growth_potential = enhanced_context.get('growth_potential', {}).get('score', 0)
        
        recommendations = []
        
        # セグメントに基づく推奨事項
        if user_segment == 'champions':
            recommendations.append({
                'title': f'🏆 限定サービスの推奨',
                'description': f'あなたの{self.agent_name}の利用状況に基づき、VIPサービスへのアップグレードを推奨します。',
                'potential_gain': 5000.0
            })
        elif user_segment == 'at_risk':
            recommendations.append({
                'title': f'💡 簡単操作の提案', 
                'description': f'あなたの{self.agent_name}のために、より簡単な操作methodを用意しました。',
                'potential_gain': 1000.0
            })
        else:
            recommendations.append({
                'title': f'📊 最適化の提案',
                'description': f'あなたのユーザープロファイルに基づき、{self.agent_name}の利用methodの最適化を提案します。',
                'potential_gain': 2000.0
            })
        
        # リスクとポテンシャルに基づくappendの推奨事項
        if churn_risk > 70:
            recommendations.append({
                'title': '🔔 専属サポート',
                'description': '私たちの専門チームが、あなたに1対1の投資指導を提供します。',
                'potential_gain': 0.0
            })
        
        if growth_potential > 70:
            recommendations.append({
                'title': '🚀 成長の機会',
                'description': f'あなたの高い成長ポテンシャルに基づき、{self.agent_name}にはさらなる発展の余地があります。',
                'potential_gain': 8000.0
            })
        
        return recommendations[:2]  # 最大2つの推奨事項を返す
    
    def _generate_insights_fallback_analysis(self, enhanced_context: Dict[str, Any]) -> Tuple[str, List[Dict[str, Any]]]:
        """
        analysisが完全に失敗した場合に、insightに基づいてフォールバックanalysisをgenerateします。
        """
        user_segment = enhanced_context.get('user_segment', 'unknown')
        
        analysis_parts = [
            f"{self.agent_name}の詳細データは一時的に利用できませんが、",
            "あなたのユーザープロファイルに基づき、価値ある提案を提供できます："
        ]
        
        if user_segment == 'champions':
            analysis_parts.append("私たちのチャンピオンユーザーとして、あなたは最高のサービスを受ける価値があります。")
        elif user_segment == 'at_risk':
            analysis_parts.append("私たちはあなたのニーズに特にnoteを払い、より良い投資体験を提供したいと考えています。")
        else:
            analysis_parts.append(f"あなたの{user_segment}の特性に基づき、専用の推奨事項をカスタマイズしました。")
        
        analysis_summary = " ".join(analysis_parts)
        recommendations = self._generate_fallback_recommendations_with_insights(enhanced_context)
        
        return analysis_summary, recommendations

    async def _get_all_assets_summary(self, portfolio: UserPortfolio) -> List[Dict[str, Any]]:
        """ポートフォリオ内の全資産の要約を取得します。"""
        pass