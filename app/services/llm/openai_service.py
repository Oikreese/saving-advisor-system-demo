from openai import AsyncOpenAI
from typing import Dict, List, Optional
from app.core.config import settings
from app.core.logging import logger

class OpenAIService:
    """OpenAI APIサービス"""
    
    def __init__(self):
        if settings.OPENAI_API_KEY:
            self.client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        else:
            logger.warning("OPENAI_API_KEY  設定されていません")
            self.client = None
    
    async def generate_completion(
        self,
        prompt: str,
        model: str = None,
        max_tokens: int = 500,
        temperature: float = 0.7,
        json_mode: bool = False
    ) -> str:
        """
        OpenAI API useしてテキストgenerate
        
        Args:
            prompt: prompt
            model: useモデル
            max_tokens: 最大トークン数
            temperature: generate 創造性
            json_mode: JSONモード 有効 するか
            
        Returns:
            str: generateされたテキスト
        """
        try:
            model = model or settings.OPENAI_MODEL
            
            if not self.client:
                # デモ用モックレスポンス
                logger.info("OPENAI_API_KEY未設定 for、モックレスポンス 返します")
                return self._generate_mock_response(prompt)
            
            params = {
                "model": model,
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": max_tokens,
                "temperature": temperature,
            }

            if json_mode:
                params["response_format"] = {"type": "json_object"}

            response = await self.client.chat.completions.create(**params)
            
            content = response.choices[0].message.content
            logger.info(f"OpenAI API レスポンスsuccess: model={model}, tokens={len(content)}")
            return content
            
        except Exception as e:
            logger.error(f"OpenAI API エラー: {e}")
            raise
    
    def _generate_mock_response(self, prompt: str) -> str:
        """
        デモ用 モックレスポンスgenerate
        
        Args:
            prompt: prompt
            
        Returns:
            str: モックレスポンス
        """
        if "ポイント" in prompt or "Points" in prompt:
            return """
            【ポイント資産分析】
            現在 ポイント残高: 15,000pt
            
            【増資提案】
            1. キャンペーン参加: 月間5つのキャンペーンに参加することで、約3,000pt獲得可能
            2. 商品レビュー: 購入商品のレビュー投稿で月500pt獲得
            3. 友達紹介: 新規ユーザー紹介で1人あたり1,000pt獲得
            
            【期待効果】
            実施により月間約4,500pt（30%増）の増資が見込まれます。
            """
        elif "売上金" in prompt or "Earnings" in prompt:
            return """
            【収入assetanalysis】
            現在 month収入: 120,000円
            
            【増資提案】
            1. 支出管理: 家計簿アプリutilize month10,000円節約
            2. 投資商品購入: 安定した商品へ 少額投資 開始
            3. スキルアップ: 副業スキル習得 収入源多様化
            
            【期待効果】
            支出最適化 投資 より、month間15,000円 assetincrease 期待 きます。
            """
        elif "モノ" in prompt or "Items" in prompt:
            return """
            【モノ資産分析】
            推定価値: 85,000円
            
            【増資提案】
            1. 未出品商品の販売: 8点の未出品商品で約25,000円の売上見込
            2. 商品価値向上: 写真・説明文改善で売上単価10%向上
            3. 購入転売: トレンド商品の購入・転売で月5,000円の利益
            
            【期待効果】
            実施により約30,000円の資産価値向上が見込まれます。
            """
        elif "ギガ" in prompt or "Giga" in prompt:
            return """
            【ギガ資産分析】
            利用可能ギガ: 15GB
            
            【増資提案】
            1. ギガ→ポイント変換: 10GBをポイントに変換して2,000pt獲得
            2. データ使用量最適化: Wi-Fi利用でギガ節約
            3. ギガチャージ特典: 特定期間のチャージでボーナスギガ獲得
            
            【期待効果】
            効率的なギガ利用により月間2,000円相当の価値創出が可能です。
            """
        elif "ステーブルコイン" in prompt or "Stablecoin" in prompt:
            return """
            【ステーブルコイン資産分析】
            現在保有額: 50,000円
            
            【増資提案】
            1. 定期積立: 月5,000円の定期積立を開始
            2. ステーキング: 年利3-5%のステーキングサービスを利用
            3. 市場動向分析: 市場レポートを参考にした戦略的投資
            
            【期待効果】
            年間約2,500円（5%）の運用益が期待できます。
            
            【注意】
            暗号資産投資にはリスクが伴います。余剰資金での投資を推奨します。
            """
        else:
            return """
            【総合assetanalysis】
            お客様 assetportfolio analysisいたします。
            
            現在 総asset: 273,000円
            
            【総合 な増資提案】
            1. Pointsutilize最適化
            2. 収入源 多様化
            3. 物品asset 効率 管理
            4. デジタルasset 戦略 運用
            
            これら 施策 より、year間約10-15% asset成長 期待 きます。
            """

from functools import lru_cache

@lru_cache()
def get_openai_service() -> OpenAIService:
    return OpenAIService()