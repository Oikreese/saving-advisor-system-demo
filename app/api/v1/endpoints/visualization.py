from fastapi import APIRouter, HTTPException, Query, Depends
from app.models.assets import AssetVisualization, UserPortfolio, UserAsset, AssetType
from app.services.utils.visualization_service import VisualizationService
from app.services.firestore.firestore_primary_service import get_firestore_primary_service, FirestorePrimaryService
from app.core.logging import logger
from typing import Optional

router = APIRouter()

# _get_portfolio_from_firestore 函数已移至 FirestorePrimaryService.get_user_portfolio

@router.get("/pie-chart/{user_id}", response_model=AssetVisualization)
async def generate_pie_chart(user_id: str, firestore_service: FirestorePrimaryService = Depends(get_firestore_primary_service)):
    """
    ユーザー資産の円グラフを生成
    
    Args:
        user_id: ユーザーID
        
    Returns:
        AssetVisualization: 円グラフ可視化データ
    """
    try:
        # ユーザーポートフォリオを取得（Firestoreから）
        portfolio = await firestore_service.get_user_portfolio(user_id, allow_empty=False, raise_http_exception=True)
        
        # 円グラフ生成
        visualization = await VisualizationService.generate_pie_chart(portfolio)
        
        logger.info(f"円グラフ生成成功: user_id={user_id}, total_value=¥{visualization.total_value:,.0f}")
        return visualization
    
    except Exception as e:
        logger.error(f"円グラフ生成エラー: {e}")
        raise HTTPException(status_code=500, detail="円グラフの生成に失敗しました")


@router.get("/{user_id}", response_model=AssetVisualization)
async def generate_visualization(
    user_id: str,
    chart_type: str = Query("pie", description="チャートタイプ。現在は 'pie' のみサポート"),
    firestore_service: FirestorePrimaryService = Depends(get_firestore_primary_service)
):
    """
    フロントエンド互換用エンドポイント。
    `/visualization/{user_id}?chart_type=pie` の形式に対応する。
    """
    chart_type = chart_type.lower()
    if chart_type not in {"pie"}:
        raise HTTPException(status_code=400, detail=f"Unsupported chart_type '{chart_type}'")

    try:
        portfolio = await firestore_service.get_user_portfolio(user_id, allow_empty=False, raise_http_exception=True)
        visualization = await VisualizationService.generate_pie_chart(portfolio)
        logger.info(f"可視化生成成功: user_id={user_id}, chart_type={chart_type}")
        return visualization
    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f"可視化生成エラー (chart_type={chart_type}): {exc}")
        raise HTTPException(status_code=500, detail="可視化データの生成に失敗しました")

@router.get("/asset-trends/{user_id}")
async def get_asset_trends(
    user_id: str,
    days: Optional[int] = Query(30, description="取得する日数")
):
    """
    資産トレンド分析 (Optional機能)
    
    Args:
        user_id: ユーザーID
        days: 取得する日数
        
    Returns:
        Dict: トレンドデータ
    """
    try:
        # TODO: 実際のトレンドデータ取得実装
        # 現在はモックデータを返す
        
        mock_trend_data = {
            "status": "mock_data",
            "message": "【資産トレンド分析機能】- 現在モックデータを使用",
            "description": "この機能は、指定された期間内のユーザーの各種資産の変化傾向を分析し、成長率、変動性、将来予測を含み、ユーザーが資産パフォーマンスを理解し最適化戦略を策定するのに役立ちます。",
            "user_id": user_id,
            "period_days": days,
            "trends": {
                "ポイント": {
                    "current_value": 15000,
                    "change_percentage": 12.5,
                    "trend": "increasing",
                    "analysis": "ポイント増加が安定しており、継続的にアクティビティに参加することをお勧めします"
                },
                "売上金・給与・報酬": {
                    "current_value": 120000,
                    "change_percentage": 5.2,
                    "trend": "stable",
                    "analysis": "収入が安定しており、投資比率を増やすことを検討できます"
                },
                "モノ": {
                    "current_value": 85000,
                    "change_percentage": -2.1,
                    "trend": "decreasing",
                    "analysis": "商品価値がわずかに下落しており、適時に販売または再価格設定することをお勧めします"
                },
                "ギガ": {
                    "current_value": 3000,
                    "change_percentage": 0.0,
                    "trend": "stable",
                    "analysis": "ギガ使用量が安定しており、特別な調整は不要です"
                },
                "ステーブルコイン": {
                    "current_value": 50000,
                    "change_percentage": 8.7,
                    "trend": "increasing",
                    "analysis": "デジタル資産のパフォーマンスが良好で、市場トレンドに合致しています"
                }
            },
            "overall_growth": 6.3,
            "current_status": "履歴モックデータを使用中、実際のトレンド分析開発中",
            "planned_features": [
                "実際の履歴データに基づくトレンド分析",
                "AI による将来資産パフォーマンスの予測",
                "パーソナライズされた投資提案",
                "リスク警告システム"
            ],
            "generated_at": "2024-01-01T00:00:00Z"
        }
        
        logger.info(f"資産トレンド取得成功 (Mock): user_id={user_id}, days={days}")
        return mock_trend_data
    
    except Exception as e:
        logger.error(f"資産トレンド取得エラー: {e}")
        raise HTTPException(status_code=500, detail="資産トレンドの取得に失敗しました")

@router.get("/portfolio-comparison/{user_id}")
async def get_portfolio_comparison(user_id: str):
    """
    ポートフォリオ比較分析 (Optional機能)
    同年代・同条件ユーザーとの比較
    
    Args:
        user_id: ユーザーID
        
    Returns:
        Dict: 比較分析データ
    """
    try:
        # TODO: 実際の比較データ取得実装
        # 現在はモックデータを返す
        
        user_portfolio = VisualizationService.generate_mock_portfolio(user_id)
        
        comparison_data = {
            "status": "mock_data",
            "message": "【ポートフォリオ比較分析機能】- 現在モックデータを使用",
            "description": "この機能は、ユーザーの資産ポートフォリオを同年代・同収入レベルの他のユーザーと比較分析し、個人資産配置の最適化提案と改善方向を提供します。",
            "user_id": user_id,
            "user_total": user_portfolio.total_assets,
            "peer_average": 250000,
            "comparison_metrics": {
                "percentile": 68,  # 上位32%
                "above_average": user_portfolio.total_assets > 250000,
                "improvement_areas": [
                    "ステーブルコイン投資の検討 - デジタル資産配置の増加を検討可能",
                    "ポイント活用の最適化 - ポイント使用戦略の最適化"
                ],
                "strong_points": [
                    "モノ資産の効率的な管理 - 商品資産管理が高効率",
                    "収入の安定性 - 収入源が比較的安定"
                ]
            },
            "recommendations": [
                "あなたの資産レベルは同年代平均を上回っています！継続維持とさらなる成長を目指しましょう。",
                "リスク分散の観点から、多様な投資商品の検討を適度にお勧めします。",
                "商品管理において優秀な成果を上げており、この経験を他の資産カテゴリーに拡張できます。"
            ],
            "current_status": "統計モックデータに基づき、実際のユーザー比較分析開発中",
            "planned_features": [
                "実際のユーザー群に基づく精密な比較",
                "地域・年齢・収入別の細分化比較分析",
                "パーソナライズされた資産配置提案",
                "同年代成功事例の学習"
            ],
            "generated_at": "2024-01-01T00:00:00Z"
        }
        
        logger.info(f"ポートフォリオ比較分析成功 (Mock): user_id={user_id}")
        return comparison_data
    
    except Exception as e:
        logger.error(f"ポートフォリオ比較分析エラー: {e}")
        raise HTTPException(status_code=500, detail="ポートフォリオ比較分析に失敗しました")