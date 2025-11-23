"""
Data Sync Service

Core business logic for synchronizing data from various sources (like BigQuery) 
to the primary data store (Firestore).

This service decouples the business logic from the task runner (Celery),
making the logic reusable and easier to test.
"""

import asyncio
from typing import List, Dict, Any
from datetime import datetime, timedelta

from app.core.logging import logger
from app.services.bigquery.enhanced_client import EnhancedBigQueryClient
from app.services.firestore.firestore_primary_service import FirestorePrimaryService
from app.core.config import settings


class DataSyncService:
    """
    Handles all data synchronization tasks between data sources and Firestore.
    """
    
    def __init__(self, 
                 bq_client: EnhancedBigQueryClient = None, 
                 firestore_service: FirestorePrimaryService = None):
        
        self.bq_client = bq_client or EnhancedBigQueryClient()
        self.firestore_service = firestore_service or FirestorePrimaryService()
        
    async def sync_mercari_trends(self):
        """
        Synchronizes Mercari trend data from BigQuery to Firestore.
        This includes hot categories and rising trend items.
        """
        logger.info("📈 市場トレンド 同期 開始します...")
        try:
            # 市場トレンドdata 取得
            trends_query = f"""
            SELECT 
              category_id,
              avg_popularity_score,
              price_trend,
              avg_success_rate,
              latest_analysis_date
            FROM `{self.bq_client.project_id}.{self.bq_client.analytics_dataset}.market_trend_analysis`
            WHERE latest_analysis_date >= DATE_SUB(CURRENT_DATE(), INTERVAL 2 DAY)
            ORDER BY avg_popularity_score DESC
            """
            
            results = self.bq_client.client.query(trends_query).result()
            categories_synced = 0
            
            # data カテゴリ別 整理
            rising_trends = []
            stable_trends = []
            falling_trends = []
            
            for row in results:
                trend_data = dict(row)
                
                if trend_data['price_trend'] == 'rising':
                    rising_trends.append(trend_data)
                elif trend_data['price_trend'] == 'falling':
                    falling_trends.append(trend_data)
                else:
                    stable_trends.append(trend_data)
                
                categories_synced += 1
            
            # Firestore save
            market_trends_cache = {
                'rising_trends': rising_trends[:20],    # 上昇トレンド上位20件
                'stable_trends': stable_trends[:10],    # 安定トレンド上位10件
                'falling_trends': falling_trends[:10],  # 下降トレンド上位10件
                'hot_categories': [t['category_id'] for t in rising_trends[:10]],
                'updated_at': datetime.now().isoformat(),
                'data_date': datetime.now().date().isoformat()
            }
            
            await self.firestore_service._mark_for_etl(
                "analytics_cache/market_trends/latest",
                market_trends_cache
            )
            
            logger.info(f"✅ 市場トレンド 同期 完了しました：{categories_synced}カテゴリ")
            return {
                'status': 'success',
                'categories_synced': categories_synced,
                'synced_at': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"市場トレンド 同期 failed: {e}")
            return {'status': 'error', 'error': str(e)}

    async def sync_all_active_users_assets(self, limit: int = 500):
        """
        Fetches all active users from BigQuery and synchronizes their asset 
        information to Firestore.
        """
        start_time = datetime.now()
        synced_users = 0
        
        try:
            # 1. 同期 必要なuserID 取得
            active_users_query = f"""
            SELECT id as user_id, created
            FROM `{self.bq_client.project_id}.{self.bq_client.mentor_dataset}.users`
            WHERE status = 'alive'
            ORDER BY created DESC
            LIMIT {limit}
            """
            
            user_results = self.bq_client.client.query(active_users_query).result()
            user_ids = [str(row['user_id']) for row in user_results]
            
            logger.info(f"{len(user_ids)}人 user assetdata 同期する必要 あります。")
            
            # 2. userasset 並行して同期
            tasks = [self.sync_assets_for_user(user_id) for user_id in user_ids]
            results = await asyncio.gather(*tasks)
            
            synced_users = sum(1 for r in results if r and r.get('status') == 'success')
            
            execution_time = (datetime.now() - start_time).total_seconds()
            
            return {
                'status': 'success',
                'synced_users': synced_users,
                'total_users_checked': len(user_ids),
                'execution_time': execution_time,
                'synced_at': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"複数user asset同期 failed: {e}")
            return {'status': 'error', 'error': str(e)}

    async def sync_assets_for_user(self, user_id: str):
        """
        Synchronizes asset data for a single user from BigQuery to Firestore.
        """
        try:
            assets_data = await self.bq_client.get_user_current_assets(user_id)
            
            if not assets_data or assets_data.get('total_estimated_value', 0) == 0:
                logger.debug(f"userID {user_id}   assetdata ないfor、スキップします。")
                return {'status': 'skipped', 'user_id': user_id}
            
            success = await self.firestore_service.save_user_assets(user_id, assets_data)
            
            if success:
                logger.debug(f"userID {user_id}  asset同期 successしました: ¥{assets_data['total_estimated_value']:,.0f}")
                return {'status': 'success', 'user_id': user_id}
            else:
                logger.warning(f"userID {user_id}  asset Firestore saveする  failed。")
                return {'status': 'error', 'error': 'Failed to save to Firestore', 'user_id': user_id}
                
        except Exception as e:
            logger.warning(f"userID {user_id}  asset同期 failed: {e}")
            return {'status': 'error', 'error': str(e), 'user_id': user_id}

    async def sync_all_active_users_insights(self, limit: int = 1000):
        """
        Fetches all active users and syncs their insights data to Firestore.
        """
        start_time = datetime.now()
        synced_users = 0
        batch_size = 100

        try:
            # 1. Get user IDs to sync
            user_ids_query = f"""
            SELECT DISTINCT user_id
            FROM `{self.bq_client.project_id}.{self.bq_client.analytics_dataset}.user_segmentation`
            WHERE analysis_created_at >= DATE_SUB(CURRENT_DATE(), INTERVAL 7 DAY)
            ORDER BY analysis_created_at DESC
            LIMIT {limit}
            """
            user_results = self.bq_client.client.query(user_ids_query).result()
            user_ids = [row['user_id'] for row in user_results]
            
            logger.info(f"{len(user_ids)}人 user インサイトdata 同期する必要 あります。")

            # 2. Batch sync user insights
            for i in range(0, len(user_ids), batch_size):
                batch_user_ids = user_ids[i:i + batch_size]
                tasks = [self.sync_insights_for_user(user_id) for user_id in batch_user_ids]
                results = await asyncio.gather(*tasks)
                
                synced_users += sum(1 for r in results if r and r.get('status') == 'success')

                if i + batch_size < len(user_ids):
                    await asyncio.sleep(0.5)
            
            execution_time = (datetime.now() - start_time).total_seconds()
            
            return {
                'status': 'success',
                'synced_users': synced_users,
                'execution_time': execution_time
            }

        except Exception as e:
            logger.error(f"複数user インサイト同期 failed: {e}")
            return {'status': 'error', 'error': str(e)}

    async def sync_insights_for_user(self, user_id: str):
        """
        Synchronizes user insights data for a single user from BigQuery to Firestore.
        """
        try:
            segmentation = await self._get_user_segmentation_batch([user_id])
            risk = await self._get_churn_risk_batch([user_id])
            growth = await self._get_growth_potential_batch([user_id])

            user_insights = self._assemble_user_insights(
                user_id,
                segmentation.get(user_id, {}),
                risk.get(user_id, {}),
                growth.get(user_id, {})
            )
            
            await self.firestore_service._mark_for_etl(
                f"analytics_cache/user_insights/{user_id}",
                user_insights
            )
            return {'status': 'success', 'user_id': user_id}
        except Exception as e:
            logger.warning(f"userID {user_id}  インサイト同期 failed: {e}")
            return {'status': 'error', 'error': str(e), 'user_id': user_id}

    # =========== Private Helper Methods for Insights Sync ===========

    async def _get_user_segmentation_batch(self, user_ids: List[str]) -> Dict[str, Any]:
        if not user_ids: return {}
        user_ids_str = "', '".join(user_ids)
        query = f"""
        SELECT user_id, user_segment, value_score, activity_score, loyalty_score, overall_score
        FROM `{self.bq_client.project_id}.{self.bq_client.analytics_dataset}.user_segmentation`
        WHERE user_id IN ('{user_ids_str}')
        """
        results = self.bq_client.client.query(query).result()
        return {row['user_id']: dict(row) for row in results}

    async def _get_churn_risk_batch(self, user_ids: List[str]) -> Dict[str, Any]:
        if not user_ids: return {}
        user_ids_str = "', '".join(user_ids)
        query = f"""
        SELECT user_id, churn_risk_score, risk_category, days_since_last_transaction, days_since_last_ai_session
        FROM `{self.bq_client.project_id}.{self.bq_client.analytics_dataset}.churn_risk_prediction`
        WHERE user_id IN ('{user_ids_str}')
        """
        results = self.bq_client.client.query(query).result()
        return {row['user_id']: dict(row) for row in results}

    async def _get_growth_potential_batch(self, user_ids: List[str]) -> Dict[str, Any]:
        if not user_ids: return {}
        user_ids_str = "', '".join(user_ids)
        query = f"""
        SELECT user_id, growth_potential_score, recommended_strategy, predicted_assets_6months, current_total_assets
        FROM `{self.bq_client.project_id}.{self.bq_client.analytics_dataset}.growth_potential_prediction`
        WHERE user_id IN ('{user_ids_str}')
        """
        results = self.bq_client.client.query(query).result()
        return {row['user_id']: dict(row) for row in results}

    def _assemble_user_insights(self, user_id: str, segmentation: Dict, risk: Dict, growth: Dict) -> Dict[str, Any]:
        return {
            'user_id': user_id,
            'user_segment': segmentation.get('user_segment', 'unknown'),
            'scores': {
                'value': int(segmentation.get('value_score', 0)),
                'activity': int(segmentation.get('activity_score', 0)),
                'loyalty': int(segmentation.get('loyalty_score', 0)),
                'overall': int(segmentation.get('overall_score', 0))
            },
            'churn_risk': {
                'score': int(risk.get('churn_risk_score', 50)),
                'category': risk.get('risk_category', 'unknown'),
                'details': {
                    'days_since_last_transaction': risk.get('days_since_last_transaction', 0),
                    'days_since_last_ai_session': risk.get('days_since_last_ai_session', 0)
                }
            },
            'growth_potential': {
                'score': int(growth.get('growth_potential_score', 50)),
                'strategy': growth.get('recommended_strategy', 'moderate_growth'),
                'predictions': {
                    'current_assets': float(growth.get('current_total_assets', 0)),
                    'predicted_6months': float(growth.get('predicted_assets_6months', 0))
                }
            },
            'cached_at': datetime.now().isoformat(),
            'ttl_hours': 2,
            'data_quality': {
                'confidence': 0.9,
                'freshness': 'cached'
            }
        }

def get_data_sync_service() -> DataSyncService:
    """Dependency injector for DataSyncService."""
    return DataSyncService()
