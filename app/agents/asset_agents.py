import asyncio
from typing import Dict, Any, List, Union, Optional, Tuple
from app.models.assets import UserPortfolio, AssetType, UserAsset
from app.models.recommendations import AgentAnalysis
from app.services.llm.openai_service import OpenAIService
from .base_agent import BaseAgent
from app.core.logging import logger
import re
import json


class PointsAgent(BaseAgent):
    """ポイント資産専門エージェント"""
    
    agent_name = "PointsAnalyzer"
    asset_type = AssetType.POINTS
    asset_name_jp = "ポイント"

    def __init__(self):
        super().__init__(agent_name=self.agent_name, asset_type=self.asset_type)
    
    # The analyze method is now inherited from BaseAgent
    
    async def _get_asset_data(self, portfolio: UserPortfolio) -> Optional[UserAsset]:
        for asset in portfolio.assets:
            if asset.asset_type.value == self.asset_type.value:
                return asset
        return None

    def _build_prompt(self, user_data: UserAsset, feedback_history: str = "") -> str:
        """ポイント分析用プロンプト構築"""
        user_data_text = f"""
        - 現在のポイント残高: {user_data.current_value}pt
        - 利用可能キャンペーン数: {user_data.metadata.get('campaigns_available', 0)}件
        """
        feedback_history_section = feedback_history

        return f"""
ユーザーのポイント資産を分析し、資産を増やすためのアドバイスを生成してください。

【ユーザー情報】
{user_data_text}

【過去のフィードバック】
{feedback_history_section}

【回答形式】
以下のJSON形式で、分析結果と具体的な推奨事項を3つ提案してください。
- findingはユーザーの状況を要約した1~2文の簡単な分析です。
-推奨事項には、`title`, `description`, `potential_gain`（円単位の期待収益）を必ず含めてください。

```json
{{
    "analysis": "<finding>",
    "recommendations": [
        {{
            "title": "推奨事項の簡潔なタイトル",
            "description": "ユーザーが取るべき具体的な行動を詳細に説明します。",
            "potential_gain": "見込み利益（日本円での**数値のみ**。文字列は不可）",
            "risk_level": "リスクレベル（「低」「中」「高」のいずれか）"
        }},
        {{
            "title": "<推奨事項2>",
            "description": "<推奨事項2の詳細な説明>",
            "potential_gain": "<金額>"
        }},
        {{
            "title": "<推奨事項3>",
            "description": "<推奨事項3の詳細な説明>",
            "potential_gain": "<金額>"
        }}
    ]
}}
```
"""

class EarningsAgent(BaseAgent):
    """収入資産専門エージェント"""
    agent_name = "EarningsAnalyzer"
    asset_type = AssetType.EARNINGS
    asset_name_jp = "売上金・給与・報酬"
    
    def __init__(self):
        super().__init__(agent_name=self.agent_name, asset_type=self.asset_type)

    # The analyze method is now inherited from BaseAgent
    
    async def _get_asset_data(self, portfolio: UserPortfolio) -> Optional[UserAsset]:
        for asset in portfolio.assets:
            if asset.asset_type.value == self.asset_type.value:
                return asset
        return None

    def _build_prompt(self, user_data: UserAsset, feedback_history: str = "") -> str:
        """収入分析用プロンプト構築"""
        user_data_text = f"""
        - 現在の資産額: {user_data.current_value}円
        - 月間収入: {user_data.metadata.get('monthly_income', 0)}円
        - 貯蓄率: {user_data.metadata.get('savings_rate', 0)*100}%
        """
        feedback_history_section = feedback_history
        return f"""
ユーザーの収入資産（売上金・給与・報酬）を分析し、資産を増やすためのアドバイスを生成してください。

【ユーザー情報】
{user_data_text}

【過去のフィードバック】
{feedback_history_section}

【回答形式】
以下のJSON形式で、分析結果と具体的な推奨事項を3つ提案してください。
- findingはユーザーの状況を要約した1~2文の簡単な分析です。
-推奨事項には、`title`, `description`, `potential_gain`（円単位の期待収益）を必ず含めてください。

```json
{{
    "analysis": "<finding>",
    "recommendations": [
        {{
            "title": "推奨事項の簡潔なタイトル",
            "description": "ユーザーが取るべき具体的な行動を詳細に説明します。",
            "potential_gain": "見込み利益（日本円での**数値のみ**。文字列は不可）",
            "risk_level": "リスクレベル（「低」「中」「高」のいずれか）"
        }},
        {{
            "title": "<推奨事項2>",
            "description": "<推奨事項2の詳細な説明>",
            "potential_gain": "<金額>"
        }},
        {{
            "title": "<推奨事項3>",
            "description": "<推奨事項3の詳細な説明>",
            "potential_gain": "<金額>"
        }}
    ]
}}
```
"""

class ItemsAgent(BaseAgent):
    """物品資産専門エージェント"""
    agent_name = "ItemsAnalyzer"
    asset_type = AssetType.ITEMS
    asset_name_jp = "モノ"
    
    def __init__(self):
        super().__init__(agent_name=self.agent_name, asset_type=self.asset_type)

    # The analyze method is now inherited from BaseAgent

    async def _get_asset_data(self, portfolio: UserPortfolio) -> Optional[UserAsset]:
        for asset in portfolio.assets:
            if asset.asset_type.value == self.asset_type.value:
                return asset
        return None

    def _build_prompt(self, user_data: UserAsset, feedback_history: str = "") -> str:
        """物品分析用プロンプト構築"""
        user_data_text = f"""
        - 物品推定価値: {user_data.current_value}円
        - 出品済み商品: {user_data.metadata.get('listed_items', 0)}点
        - 未出品商品: {user_data.metadata.get('unlisted_items', 0)}点
        """
        feedback_history_section = feedback_history
        return f"""
ユーザーの物品資産（所有アイテム）を分析し、資産を増やすためのアドバイスを生成してください。

【ユーザー情報】
{user_data_text}

【過去のフィードバック】
{feedback_history_section}

【回答形式】
以下のJSON形式で、分析結果と具体的な推奨事項を3つ提案してください。
- findingはユーザーの状況を要約した1~2文の簡単な分析です。
-推奨事項には、`title`, `description`, `potential_gain`（円単位の期待収益）を必ず含めてください。

```json
{{
    "analysis": "<finding>",
    "recommendations": [
        {{
            "title": "推奨事項の簡潔なタイトル",
            "description": "ユーザーが取るべき具体的な行動を詳細に説明します。",
            "potential_gain": "見込み利益（日本円での**数値のみ**。文字列は不可）",
            "risk_level": "リスクレベル（「低」「中」「高」のいずれか）"
        }},
        {{
            "title": "<推奨事項2>",
            "description": "<推奨事項2の詳細な説明>",
            "potential_gain": "<金額>"
        }},
        {{
            "title": "<推奨事項3>",
            "description": "<推奨事項3の詳細な説明>",
            "potential_gain": "<金額>"
        }}
    ]
}}
```
"""

class GigaAgent(BaseAgent):
    """ギガ資産専門エージェント"""
    agent_name = "GigaAnalyzer"
    asset_type = AssetType.GIGA
    asset_name_jp = "ギガ"
    
    def __init__(self):
        super().__init__(agent_name=self.agent_name, asset_type=self.asset_type)
    
    # The analyze method is now inherited from BaseAgent

    async def _get_asset_data(self, portfolio: UserPortfolio) -> Optional[UserAsset]:
        for asset in portfolio.assets:
            if asset.asset_type.value == self.asset_type.value:
                return asset
        return None

    def _build_prompt(self, user_data: UserAsset, feedback_history: str = "") -> str:
        """ギガ分析用プロンプト構築"""
        user_data_text = f"""
        - ギガ資産価値: {user_data.current_value}円
        - 利用可能ギガ: {user_data.metadata.get('available_giga', 0)}GB
        - ポイント変換レート: {user_data.metadata.get('conversion_rate', 0)}円/GB
        """
        feedback_history_section = feedback_history
        return f"""
ユーザーのギガ資産（データ通信量）を分析し、資産を増やすためのアドバイスを生成してください。

【ユーザー情報】
{user_data_text}

【過去のフィードバック】
{feedback_history_section}

【回答形式】
以下のJSON形式で、分析結果と具体的な推奨事項を3つ提案してください。
- findingはユーザーの状況を要約した1~2文の簡単な分析です。
-推奨事項には、`title`, `description`, `potential_gain`（円単位の期待収益）を必ず含めてください。

```json
{{
    "analysis": "<finding>",
    "recommendations": [
        {{
            "title": "推奨事項の簡潔なタイトル",
            "description": "ユーザーが取るべき具体的な行動を詳細に説明します。",
            "potential_gain": "見込み利益（日本円での**数値のみ**。文字列は不可）",
            "risk_level": "リスクレベル（「低」「中」「高」のいずれか）"
        }},
        {{
            "title": "<推奨事項2>",
            "description": "<推奨事項2の詳細な説明>",
            "potential_gain": "<金額>"
        }},
        {{
            "title": "<推奨事項3>",
            "description": "<推奨事項3の詳細な説明>",
            "potential_gain": "<金額>"
        }}
    ]
}}
```
"""

class StablecoinAgent(BaseAgent):
    """ステーブルコイン資産専門エージェント"""
    agent_name = "StablecoinAnalyzer"
    asset_type = AssetType.STABLECOIN
    asset_name_jp = "ステーブルコイン"
    
    def __init__(self):
        super().__init__(agent_name=self.agent_name, asset_type=self.asset_type)

    # The analyze method is now inherited from BaseAgent
    
    async def _get_asset_data(self, portfolio: UserPortfolio) -> Optional[UserAsset]:
        for asset in portfolio.assets:
            if asset.asset_type.value == self.asset_type.value:
                return asset
        return None

    def _build_prompt(self, user_data: UserAsset, feedback_history: str = "") -> str:
        """ステーブルコイン分析用プロンプト構築"""
        user_data_text = f"""
        - 現在保有額: {user_data.current_value}円
        - リスク承認: {user_data.metadata.get('risk_approved', False)}
        - 投資経験: {user_data.metadata.get('investment_experience', 'beginner')}
        - リスクプロファイル: {user_data.metadata.get('risk_profile', 'medium')}
        """
        feedback_history_section = feedback_history
        return f"""
ユーザーのステーブルコイン資産を分析し、資産を増やすためのアドバイスを生成してください。

【ユーザー情報】
{user_data_text}

【過去のフィードバック】
{feedback_history_section}

【回答形式】
以下のJSON形式で、分析結果と具体的な推奨事項を3つ提案してください。
- findingはユーザーの状況を要約した1~2文の簡単な分析です。
-推奨事項には、`title`, `description`, `potential_gain`（円単位の期待収益）を必ず含めてください。

```json
{{
    "analysis": "<finding>",
    "recommendations": [
        {{
            "title": "推奨事項の簡潔なタイトル",
            "description": "ユーザーが取るべき具体的な行動を詳細に説明します。",
            "potential_gain": "見込み利益（日本円での**数値のみ**。文字列は不可）",
            "risk_level": "リスクレベル（「低」「中」「高」のいずれか）"
        }},
        {{
            "title": "<推奨事項2>",
            "description": "<推奨事項2の詳細な説明>",
            "potential_gain": "<金額>"
        }},
        {{
            "title": "<推奨事項3>",
            "description": "<推奨事項3の詳細な説明>",
            "potential_gain": "<金額>"
        }}
    ]
}}
```
"""

class GeneralPortfolioAnalyzer(BaseAgent):
    """
    ポートフォリオ全体を分析し、総合的な評価を生成するエージェント
    """
    agent_name = "GeneralPortfolioAnalyzer"
    asset_type = None # This agent analyzes the whole portfolio
    asset_name_jp = "総合分析"

    def __init__(self):
        # We pass asset_type=None as this agent doesn't specialize
        super().__init__(agent_name=self.agent_name, asset_type=self.asset_type)

    async def _get_asset_data(self, portfolio: UserPortfolio) -> UserPortfolio:
        """
        このエージェントはポートフォリオ全体をデータとして使用します
        """
        return portfolio
    
    async def analyze(
        self, portfolio: UserPortfolio, feedback_history: str = ""
    ) -> Tuple[str, List[Dict[str, Any]]]:
        """
        総合分析エージェントのカスタム分析ロジック
        """
        # We want to leverage the base analyze method but ensure no recommendations are returned
        analysis_summary, _ = await super().analyze(portfolio, feedback_history)
        return analysis_summary, []


    def _build_prompt(self, user_data: UserPortfolio, feedback_history: str = "") -> str:
        """
        ポートフォリオ全体の分析用プロンプトを構築
        """
        assets_summary = []
        for asset in user_data.assets:
            assets_summary.append(
                f"- {asset.asset_type.value}: {asset.current_value:,.0f}円"
            )
        
        assets_summary_str = "\n".join(assets_summary)
        feedback_history_section = feedback_history

        return f"""
ユーザーの資産ポートフォリオ全体を分析し、150字以内で簡潔な総合評価を生成してください。

【ユーザーの資産概要】
- 総資産: {user_data.total_assets:,.0f}円
{assets_summary_str}

【過去のフィードバック】
{feedback_history_section}

【回答形式】
以下のJSON形式で、"analysis"フィールドに分析結果のみを記述してください。推奨事項は不要です。

```json
{{
    "analysis": "<ここに150字以内の総合評価を記述>"
}}
```
"""