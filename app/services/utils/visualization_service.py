from typing import Dict, List
import plotly.graph_objs as go
import plotly.utils
import json
from app.models.assets import UserPortfolio, AssetVisualization, AssetType
from app.core.logging import logger

class VisualizationService:
    """可视化服务"""
    """資産可視化サービス"""
    
    @staticmethod
    async def generate_pie_chart(portfolio: UserPortfolio) -> AssetVisualization:
        """
        ユーザーポートフォリオから円グラフを生成
        
        Args:
            portfolio: ユーザーポートフォリオデータ
            
        Returns:
            AssetVisualization: 可視化データ
        """
        try:
            # 資産タイプ別の集計
            asset_breakdown = {}
            labels = []
            values = []
            colors = []
            
            # 各資産タイプの色定義
            asset_colors = {
                AssetType.POINTS: "#FF6B6B",
                AssetType.EARNINGS: "#4ECDC4", 
                AssetType.ITEMS: "#45B7D1",
                AssetType.GIGA: "#96CEB4",
                AssetType.STABLECOIN: "#FECA57"
            }
            
            # ポートフォリオから資産を集計
            for asset in portfolio.assets:
                asset_type = asset.asset_type
                if asset_type in asset_breakdown:
                    asset_breakdown[asset_type] += asset.current_value
                else:
                    asset_breakdown[asset_type] = asset.current_value
            
            # 円グラフ用のデータ準備
            for asset_type, value in asset_breakdown.items():
                if value > 0:  # 0以上の資産のみ表示
                    labels.append(asset_type)
                    values.append(value)
                    colors.append(asset_colors.get(asset_type, "#95A5A6"))
            
            # Plotlyで円グラフ生成
            fig = go.Figure(data=[
                go.Pie(
                    labels=labels,
                    values=values,
                    hole=.3,  # ドーナツ型に
                    marker=dict(colors=colors),
                    textinfo='label+percent+value',
                    textfont=dict(size=12),
                    hovertemplate='<b>%{label}</b><br>' +
                                  '金額: ¥%{value:,.0f}<br>' +
                                  '割合: %{percent}<br>' +
                                  '<extra></extra>'
                )
            ])
            
            # レイアウト設定
            fig.update_layout(
                title=dict(
                    text=f"資産ポートフォリオ (総額: ¥{portfolio.total_assets:,.0f})",
                    x=0.5,
                    font=dict(size=16, color="#2C3E50")
                ),
                font=dict(family="Arial, sans-serif", size=12),
                showlegend=True,
                legend=dict(
                    orientation="v",
                    yanchor="middle",
                    y=0.5,
                    xanchor="left",
                    x=1.01
                ),
                margin=dict(t=60, b=20, l=20, r=150),
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)'
            )
            
            # JSON形式のチャートデータ
            chart_data = json.loads(plotly.utils.PlotlyJSONEncoder().encode(fig))
            
            return AssetVisualization(
                user_id=portfolio.user_id,
                chart_type="pie",
                chart_data=chart_data,
                total_value=portfolio.total_assets,
                asset_breakdown={k: v for k, v in asset_breakdown.items()}
            )
            
        except Exception as e:
            logger.error(f"円グラフ生成エラー: {e}")
            raise
    
    @staticmethod
    async def generate_bar_chart(portfolio: UserPortfolio) -> Dict:
        """
        資産の棒グラフを生成 (Optional機能)
        
        Args:
            portfolio: ユーザーポートフォリオデータ
            
        Returns:
            Dict: 棒グラフのJSON データ
        """
        try:
            # 資産タイプ別の集計
            asset_breakdown = {}
            for asset in portfolio.assets:
                asset_type = asset.asset_type
                if asset_type in asset_breakdown:
                    asset_breakdown[asset_type] += asset.current_value
                else:
                    asset_breakdown[asset_type] = asset.current_value
            
            # 棒グラフ生成
            fig = go.Figure([
                go.Bar(
                    x=list(asset_breakdown.keys()),
                    y=list(asset_breakdown.values()),
                    marker_color=['#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4', '#FECA57']
                )
            ])
            
            fig.update_layout(
                title="資産別金額比較",
                xaxis_title="資産タイプ",
                yaxis_title="金額 (¥)",
                showlegend=False
            )
            
            return json.loads(plotly.utils.PlotlyJSONEncoder().encode(fig))
            
        except Exception as e:
            logger.error(f"棒グラフ生成エラー: {e}")
            raise
    
    @staticmethod
    def generate_mock_portfolio(user_id: str) -> UserPortfolio:
        """
        テスト用のモックポートフォリオデータを生成
        
        Args:
            user_id: ユーザーID
            
        Returns:
            UserPortfolio: モックポートフォリオ
        """
        from app.models.assets import UserAsset
        from datetime import datetime
        
        mock_assets = [
            UserAsset(
                user_id=user_id,
                asset_type=AssetType.POINTS,
                current_value=15000,
                metadata={"source": "mercari_points", "campaigns_available": 5}
            ),
            UserAsset(
                user_id=user_id,
                asset_type=AssetType.EARNINGS,
                current_value=120000,
                metadata={"monthly_income": 40000, "savings_rate": 0.25}
            ),
            UserAsset(
                user_id=user_id,
                asset_type=AssetType.ITEMS,
                current_value=85000,
                metadata={"listed_items": 12, "unlisted_items": 8}
            ),
            UserAsset(
                user_id=user_id,
                asset_type=AssetType.GIGA,
                current_value=3000,
                metadata={"available_giga": 15, "conversion_rate": 200}
            ),
            UserAsset(
                user_id=user_id,
                asset_type=AssetType.STABLECOIN,
                current_value=50000,
                metadata={"risk_approved": True, "investment_experience": "beginner"}
            )
        ]
        
        total_assets = sum(asset.current_value for asset in mock_assets)
        
        return UserPortfolio(
            user_id=user_id,
            total_assets=total_assets,
            assets=mock_assets,
            last_analyzed=datetime.now()
        )


# 全局实例
_visualization_service = None

def get_visualization_service():
    """获取可视化服务实例"""
    global _visualization_service
    if _visualization_service is None:
        _visualization_service = VisualizationService()
    return _visualization_service