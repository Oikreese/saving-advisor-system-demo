from typing import Dict, List
from datetime import datetime, timedelta
from app.models.recommendations import (
    ComprehensiveRecommendation, UserTask, MonthlyTaskList, 
    AssetRecommendation, RecommendationStatus
)
from app.models.assets import AssetType, UserPortfolio
from app.services.llm.openai_service import OpenAIService
from app.core.logging import logger
import uuid
import re

class TaskService:
    """タスク管理サービス"""
    
    @staticmethod
    async def generate_comprehensive_recommendation(
        user_id: str,
        portfolio: UserPortfolio,
        asset_recommendations: List[AssetRecommendation],
        accepted_recommendation_ids: List[str] = []
    ) -> ComprehensiveRecommendation:
        """
        総合推奨事項を生成
        """
        try:
            # 選択された推奨事項から期待される利益の合計を計算
            total_gains = 0.0
            accepted_titles = []
            for rec_str in accepted_recommendation_ids:
                try:
                    # 新しいフォーマット（|区切り）か古いフォーマット（_区切り）かを確認
                    if '|' in rec_str:
                        # 新フォーマット：recommendation_id|title|potential_gain
                        parts = rec_str.split('|')
                        accepted_titles.append(parts[1])
                        total_gains += float(parts[2])
                    else:
                        # 旧フォーマット：user_id_agent_name_asset_name_index
                        # 推薦IDを解析して意味のある情報を抽出
                        parts = rec_str.split('_')
                        if len(parts) >= 3:
                            # 資産タイプ名をタイトルとして抽出
                            asset_name = parts[2] if len(parts) > 2 else "Unknown"
                            accepted_titles.append(asset_name)
                            # IDからpotential_gainを取得できないため、デフォルト値を使用
                            total_gains += 1000.0  # 各推薦にデフォルトで1000円の潜在的利益
                        else:
                            logger.warning(f"Invalid recommendation ID format: {rec_str}")
                            accepted_titles.append("未知の推薦")
                            total_gains += 1000.0
                except (IndexError, ValueError) as e:
                    logger.warning(f"Could not parse accepted recommendation string: {rec_str} - Error: {e}")
                    # 完全な失敗を避けるためにデフォルト値を提供
                    accepted_titles.append("未知の推薦")
                    total_gains += 1000.0

            initial_assets = portfolio.total_assets
            predicted_assets = initial_assets + total_gains

            # LLMを使用して最終的なサマリーを生成
            comprehensive_summary = await TaskService._generate_final_summary_with_llm(
                initial_assets, predicted_assets, accepted_titles
            )

            comprehensive_rec = ComprehensiveRecommendation(
                user_id=user_id,
                asset_recommendations=[], # This field is not directly used in the response
                accepted_recommendations=accepted_recommendation_ids,
                total_expected_growth=total_gains,
                overall_risk_level="medium", # Simplified risk level
                implementation_priority=[], # Simplified priority
                initial_assets=initial_assets,
                predicted_assets=predicted_assets,
                comprehensive_summary=comprehensive_summary
            )
            
            logger.info(f"総合推奨事項生成完了: user_id={user_id}, growth=¥{total_gains:,.0f}")
            return comprehensive_rec
            
        except Exception as e:
            logger.error(f"総合推奨事項生成エラー: {e}")
            raise

    @staticmethod
    async def _generate_final_summary_with_llm(initial_assets: float, predicted_assets: float, accepted_titles: List[str]) -> str:
        """LLMを使用して最終的なサマリーコメントを生成"""
        try:
            llm_service = OpenAIService()
            
            accepted_actions_str = "\n".join([f"- {title}" for title in accepted_titles])
            
            prompt = f"""
            ユーザーが以下の資産増加施策を実行することを選択しました。
            現在の総資産は {initial_assets:,.0f}円で、これらの施策を実行した後の予測総資産は {predicted_assets:,.0f}円です。
            これにより、{predicted_assets - initial_assets:,.0f}円の資産増加が見込まれます。
            
            実行予定の施策:
            {accepted_actions_str}

            ファイナンシャルアドバイザーとして、ユーザーの選択を称賛し、以下の要素を含んだ前向きで具体的な最終コメントを200字以内で生成してください。
            1. 予測される資産増加についての要約。
            2. 選択された施策の重要性についての言及。
            3. 次のステップである月間タスクを完了させることが、予測を実現するために重要であるという激励。
            """

            summary = await llm_service.generate_completion(prompt, max_tokens=400)
            return summary.strip()

        except Exception as e:
            logger.error(f"LLMによる最終サマリー生成エラー: {e}")
            return "選択されたアドバイスの実行により、着実な資産増加が期待できます。計画的にタスクを進めていきましょう。"

    @staticmethod
    async def generate_monthly_tasks(
        user_id: str,
        comprehensive_recommendation: ComprehensiveRecommendation,
        target_month: str = None
    ) -> MonthlyTaskList:
        """
        月間タスクリストを生成
        
        Args:
            user_id: ユーザーID
            comprehensive_recommendation: 総合推奨事項
            target_month: 対象月 (YYYY-MM, デフォルトは現在月)
            
        Returns:
            MonthlyTaskList: 月間タスクリスト
        """
        try:
            if not target_month:
                target_month = datetime.now().strftime("%Y-%m")
            
            tasks = []
            total_reward = 0.0
            
            # 受諾された推奨事項から重複しない資産タイプを取得
            accepted_recs = [
                rec for rec in comprehensive_recommendation.asset_recommendations
                if rec.recommendation_id in comprehensive_recommendation.accepted_recommendations
            ]
            
            unique_asset_types = {rec.asset_type for rec in accepted_recs}
            
            # 各資産タイプに対して一度だけタスクを生成
            for asset_type in unique_asset_types:
                # この資産タイプに関連する最初の推奨事項を見つける（タスク生成のコンテキストとして使用）
                related_rec = next((rec for rec in accepted_recs if rec.asset_type == asset_type), None)
                if related_rec:
                    asset_tasks = TaskService._generate_tasks_for_recommendation(
                        user_id, related_rec, target_month
                    )
                    tasks.extend(asset_tasks)

            # 全般的な資産管理タスクを追加
            general_tasks = TaskService._generate_general_tasks(user_id, target_month)
            tasks.extend(general_tasks)
            
            # タスクの総数を8個に制限
            final_tasks = tasks[:8]
            total_reward = sum(task.completion_reward or 0 for task in final_tasks)

            monthly_task_list = MonthlyTaskList(
                user_id=user_id,
                month=target_month,
                tasks=final_tasks,
                total_tasks=len(final_tasks),
                completed_tasks=0,
                estimated_total_reward=total_reward
            )
            
            logger.info(f"月間タスクリスト生成完了: user_id={user_id}, tasks={len(final_tasks)}")
            return monthly_task_list
            
        except Exception as e:
            logger.error(f"月間タスクリスト生成エラー: {e}")
            raise

    @staticmethod
    async def predict_total_reward_with_llm(tasks: List[UserTask]) -> str:
        """
        LLMを使用して、タスクリスト全体から期待される総リワードを予測します。
        """
        try:
            llm_service = OpenAIService()
            
            task_descriptions = "\n".join([f"- {task.title} (報酬: {task.completion_reward}円)" for task in tasks])
            
            prompt = f"""
            以下は、あるユーザーの資産を増やすための1ヶ月間のタスクリストです。
            これらのタスクをすべて完了した場合に期待される現実的な総収益（円）を予測し、その金額と簡単な根拠を述べてください。
            予測は単なる報酬の合計ではなく、タスクの相乗効果や実行のしやすさも考慮してください。

            タスクリスト:
            {task_descriptions}

            回答は以下の形式でお願いします。
            予測総収益: [金額]円
            根拠: [簡単な根拠]
            """

            response = await llm_service.generate_completion(prompt)

            # Extract the predicted amount from the response
            match = re.search(r"予測総収益:.*?(\d{1,3}(,\d{3})*|\d+)", response)
            if match:
                predicted_amount = match.group(1).replace(",", "")
                # Find the reasoning part as well
                reasoning_match = re.search(r"根拠:\s*(.*)", response, re.DOTALL)
                reasoning = reasoning_match.group(1).strip() if reasoning_match else "根拠が提供されませんでした。"
                return f"約 {predicted_amount}円 ({reasoning})"
            else:
                return "予測額を抽出できませんでした。詳細はLLMの応答を確認してください。"

        except Exception as e:
            logger.error(f"LLMによる総リワード予測エラー: {e}")
            return "収益予測中にエラーが発生しました。"
    
    @staticmethod
    def _determine_implementation_priority(
        accepted_recommendations: List[AssetRecommendation]
    ) -> List[str]:
        """
        実装優先順位を決定
        
        Args:
            accepted_recommendations: 受諾された推奨事項
            
        Returns:
            List[str]: 優先順位付けされた推奨ID
        """
        # 優先順位の基準:
        # 1. 期待効果が高い
        # 2. 信頼度スコアが高い  
        # 3. リスクが低い
        
        risk_scores = {"low": 3, "medium": 2, "high": 1}
        
        def priority_score(rec):
            return (
                rec.expected_impact * 0.4 +          # 期待効果 (40%)
                rec.confidence_score * 10000 * 0.4 + # 信頼度 (40%) 
                risk_scores[rec.risk_level] * 1000 * 0.2  # リスク (20%)
            )
        
        sorted_recs = sorted(
            accepted_recommendations, 
            key=priority_score, 
            reverse=True
        )
        
        return [rec.recommendation_id for rec in sorted_recs]
    
    @staticmethod
    def _generate_tasks_for_recommendation(
        user_id: str, 
        recommendation: AssetRecommendation, 
        month: str
    ) -> List[UserTask]:
        """
        推奨事項からタスクを生成
        
        Args:
            user_id: ユーザーID
            recommendation: 推奨事項
            month: 対象月
            
        Returns:
            List[UserTask]: タスクリスト
        """
        tasks = []
        base_due_date = datetime.now() + timedelta(days=30)
        
        # 資産タイプ別のタスク生成
        if recommendation.asset_type == AssetType.POINTS:
            tasks.extend([
                UserTask(
                    task_id=str(uuid.uuid4()),
                    user_id=user_id,
                    title="ポイントキャンペーンの確認",
                    description="今月の利用可能なポイントキャンペーンを確認し、参加登録する",
                    related_asset_type=AssetType.POINTS,
                    related_recommendation_id=recommendation.recommendation_id,
                    due_date=base_due_date,
                    completion_reward=500.0
                ),
                UserTask(
                    task_id=str(uuid.uuid4()),
                    user_id=user_id,
                    title="商品レビューの投稿",
                    description="購入した商品のレビューを投稿してポイントを獲得する",
                    related_asset_type=AssetType.POINTS,
                    related_recommendation_id=recommendation.recommendation_id,
                    due_date=base_due_date + timedelta(days=7),
                    completion_reward=300.0
                )
            ])
        
        elif recommendation.asset_type == AssetType.EARNINGS:
            tasks.extend([
                UserTask(
                    task_id=str(uuid.uuid4()),
                    user_id=user_id,
                    title="月間支出の見直し",
                    description="家計簿をチェックして無駄な支出を特定し、削減プランを立てる",
                    related_asset_type=AssetType.EARNINGS,
                    related_recommendation_id=recommendation.recommendation_id,
                    due_date=base_due_date,
                    completion_reward=1000.0
                ),
                UserTask(
                    task_id=str(uuid.uuid4()),
                    user_id=user_id,
                    title="投資商品の調査",
                    description="安定した投資商品について情報収集し、投資検討する",
                    related_asset_type=AssetType.EARNINGS,
                    related_recommendation_id=recommendation.recommendation_id,
                    due_date=base_due_date + timedelta(days=14),
                    completion_reward=2000.0
                )
            ])
        
        elif recommendation.asset_type == AssetType.ITEMS:
            tasks.extend([
                UserTask(
                    task_id=str(uuid.uuid4()),
                    user_id=user_id,
                    title="未出品商品の整理",
                    description="未出品商品を整理し、出品可能な商品をリストアップする",
                    related_asset_type=AssetType.ITEMS,
                    related_recommendation_id=recommendation.recommendation_id,
                    due_date=base_due_date,
                    completion_reward=800.0
                ),
                UserTask(
                    task_id=str(uuid.uuid4()),
                    user_id=user_id,
                    title="商品写真の改善",
                    description="出品商品の写真を撮り直して、より魅力的な画像に更新する",
                    related_asset_type=AssetType.ITEMS,
                    related_recommendation_id=recommendation.recommendation_id,
                    due_date=base_due_date + timedelta(days=10),
                    completion_reward=1200.0
                )
            ])
        
        elif recommendation.asset_type == AssetType.GIGA:
            tasks.append(
                UserTask(
                    task_id=str(uuid.uuid4()),
                    user_id=user_id,
                    title="ギガ使用量の確認",
                    description="今月のギガ使用量を確認し、余剰分をポイントに変換する",
                    related_asset_type=AssetType.GIGA,
                    related_recommendation_id=recommendation.recommendation_id,
                    due_date=base_due_date,
                    completion_reward=400.0
                )
            )
        
        elif recommendation.asset_type == AssetType.STABLECOIN:
            tasks.extend([
                UserTask(
                    task_id=str(uuid.uuid4()),
                    user_id=user_id,
                    title="投資リスクの再評価",
                    description="現在のリスク許容度を再評価し、投資戦略を見直す",
                    related_asset_type=AssetType.STABLECOIN,
                    related_recommendation_id=recommendation.recommendation_id,
                    due_date=base_due_date,
                    completion_reward=1500.0
                ),
                UserTask(
                    task_id=str(uuid.uuid4()),
                    user_id=user_id,
                    title="定期積立の設定",
                    description="ステーブルコインの定期積立サービスを設定する",
                    related_asset_type=AssetType.STABLECOIN,
                    related_recommendation_id=recommendation.recommendation_id,
                    due_date=base_due_date + timedelta(days=7),
                    completion_reward=2500.0
                )
            ])
        
        return tasks
    
    @staticmethod
    def _generate_general_tasks(user_id: str, month: str) -> List[UserTask]:
        """
        全般的な資産管理タスクを生成
        
        Args:
            user_id: ユーザーID
            month: 対象月
            
        Returns:
            List[UserTask]: 全般タスクリスト
        """
        base_due_date = datetime.now() + timedelta(days=30)
        
        return [
            UserTask(
                task_id=str(uuid.uuid4()),
                user_id=user_id,
                title="月次資産レポートの確認",
                description="今月の資産状況レポートを確認し、目標達成度をチェックする",
                due_date=base_due_date,
                completion_reward=300.0
            ),
            UserTask(
                task_id=str(uuid.uuid4()),
                user_id=user_id,
                title="来月の資産目標設定",
                description="来月の資産増加目標を設定し、具体的なアクションプランを立てる",
                due_date=base_due_date + timedelta(days=25),
                completion_reward=500.0
            )
        ]


# 全局实例
_task_service = None

def get_task_service():
    """获取任务服务实例"""
    global _task_service
    if _task_service is None:
        _task_service = TaskService()
    return _task_service