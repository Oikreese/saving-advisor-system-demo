"""
System Performance Monitoring Service

Aggregates real-time performance metrics from various parts of the application,
including Celery services and system resources.
"""
import psutil
import asyncio
import httpx
import shutil
import time
from typing import Dict, Any, List
from datetime import datetime
from pathlib import Path

from app.core.logging import logger
from app.services.utils.service_manager import unified_service_manager
from app.core.config import settings

class MonitoringService:
    """
    Collects and formats system performance and application health data.
    """
    
    def __init__(self):
        self._client = None
    
    async def get_http_client(self):
        """共有HTTPクライアント 取得し、接続再作成 オーバーヘッド 回避します"""
        if self._client is None:
            self._client = httpx.AsyncClient(
                timeout=3.0,
                limits=httpx.Limits(max_keepalive_connections=5, max_connections=10)
            )
        return self._client
    
    async def close(self):
        """HTTPクライアント 閉じます"""
        if self._client:
            await self._client.aclose()
            self._client = None

    async def get_system_metrics(self) -> Dict[str, Any]:
        """
        Gathers and returns business KPIs as defined in the Performance Monitoring Guide.
        """
        if not settings.ENABLE_MONITORING:
            return {
                "timestamp": datetime.now().isoformat(),
                "monitoring_disabled": True,
                "business_kpis": {"status": "monitoring_disabled"}
            }
        
        # Get business performance metrics
        if settings.MONITORING_LITE_MODE:
            # ライトモード：基本KPI み チェック
            business_kpis = await self._get_lite_business_kpis()
        else:
            # フルモード：すべて KPI チェック
            business_kpis = await self._get_business_kpis()
        
        return {
            "timestamp": datetime.now().isoformat(),
            "business_kpis": business_kpis
        }

    async def _get_business_kpis(self) -> Dict[str, Any]:
        """ビジネスKPI 取得（パフォーマンスモニタリングガイド 基づく）"""
        try:
            health_check_kpi, recommendation_kpi, cache_kpi, sync_kpi, availability_kpi = await asyncio.gather(
                self._get_health_check_kpi(),
                self._get_recommendation_kpi(),
                self._get_cache_hit_rate_kpi(),
                self._get_sync_performance_kpi(),
                self._get_availability_kpi(),
                return_exceptions=True
            )
            
            all_kpis = {
                "health_check": health_check_kpi if not isinstance(health_check_kpi, Exception) else {"status": "error", "error": str(health_check_kpi)},
                "recommendation_api": recommendation_kpi if not isinstance(recommendation_kpi, Exception) else {"status": "error", "error": str(recommendation_kpi)},
                "cache_hit_rate": cache_kpi if not isinstance(cache_kpi, Exception) else {"status": "error", "error": str(cache_kpi)},
                "sync_performance": sync_kpi if not isinstance(sync_kpi, Exception) else {"status": "error", "error": str(sync_kpi)},
                "availability": availability_kpi if not isinstance(availability_kpi, Exception) else {"status": "error", "error": str(availability_kpi)}
            }
            
            # 全体 なKPIステータス 計算
            overall_status = self._calculate_business_kpi_status(all_kpis)
            all_kpis["overall"] = overall_status
            
            return all_kpis
        except Exception as e:
            logger.error(f"ビジネスKPI 取得 failed: {e}")
            return {
                "health_check": {"status": "error", "error": str(e)},
                "overall": {"status": "error", "message": "KPIチェックfailed"}
            }

    async def _get_lite_business_kpis(self) -> Dict[str, Any]:
        """ライトモード ビジネスKPIチェック - 最も重要な指標 み チェックし、リソース消費 削減"""
        try:
            # ヘルスチェック み 行い、他 KPI キャッシュ値また 簡略化されたチェック use
            health_check_kpi = await self._get_health_check_kpi()
            
            # 簡略化されたステータスチェック
            lite_kpis = {
                "health_check": health_check_kpi,
                "recommendation_api": {"status": "skipped", "reason": "lite_mode"},
                "cache_hit_rate": {"status": "skipped", "reason": "lite_mode"},
                "sync_performance": {"sync_enabled": settings.ENABLE_ANALYTICS_SYNC, "status": "good" if settings.ENABLE_ANALYTICS_SYNC else "poor"},
                "availability": {"availability_percent": 100.0 if health_check_kpi.get("available") else 0.0, "status": "excellent" if health_check_kpi.get("available") else "poor"}
            }
            
            # 全体 なステータス 計算
            overall_status = {"status": "good", "message": "軽量監視モード", "mode": "lite"}
            lite_kpis["overall"] = overall_status
            
            return lite_kpis
        except Exception as e:
            logger.error(f"ライトモード KPIチェック failed: {e}")
            return {
                "health_check": {"status": "error", "error": str(e)},
                "overall": {"status": "error", "message": "軽量監視チェックfailed"}
            }

    async def _get_health_check_kpi(self) -> Dict[str, Any]:
        """ヘルスチェック応答時間 KPI: < 50ms"""
        try:
            # 高精度タイマー use
            start_time = time.perf_counter()
            client = await self.get_http_client()
            response = await client.get(f"http://localhost:8080/api/v1/health")
            end_time = time.perf_counter()
            
            response_time_ms = (end_time - start_time) * 1000
            
            return {
                "response_time_ms": round(response_time_ms, 1),
                "target_ms": 50,
                "status": "excellent" if response_time_ms < 50 else "good" if response_time_ms < 100 else "poor",
                "available": response.status_code == 200
            }
        except Exception as e:
            return {"status": "error", "error": str(e), "available": False}

    async def _get_recommendation_kpi(self) -> Dict[str, Any]:
        """recommendationAPI応答時間 KPI: シンプルなrecommendation < 2秒, 複雑なanalysis < 15秒"""
        try:
            start_time = time.perf_counter()
            client = await self.get_http_client()
            
            # Try with a timeout to avoid hanging
            try:
                response = await asyncio.wait_for(
                    client.get(f"http://localhost:8080/api/v1/recommendations-firestore-primary/analyze/1001"),
                    timeout=15.0  # 15 second timeout for complex analysis
                )
            except asyncio.TimeoutError:
                return {
                    "status": "error", 
                    "error": "Request timeout (>15s)", 
                    "available": False,
                    "response_time_s": None
                }
            except httpx.ConnectError as e:
                logger.warning(f"Recommendation API connection error: {e}")
                return {
                    "status": "error", 
                    "error": "Connection failed - service may be down", 
                    "available": False,
                    "response_time_s": None
                }
            
            end_time = time.perf_counter()
            response_time_s = end_time - start_time
            recommendations_count = 0
            
            if response.status_code == 200:
                try:
                    data = response.json()
                    recommendations_count = len(data.get("consensus_recommendations", []))
                except:
                    recommendations_count = 0
                
                # analysisタイプ 判断
                category = "簡単analysis" if response_time_s < 2 else "複雑analysis"
                
                # タイプ based onパフォーマンス 判断
                if category == "簡単analysis":
                    status = "excellent" if response_time_s < 1 else "good" if response_time_s < 2 else "poor"
                else:
                    status = "excellent" if response_time_s < 5 else "good" if response_time_s < 15 else "poor"
                
                return {
                    "response_time_s": round(response_time_s, 2),
                    "category": category,
                    "recommendations_generated": recommendations_count,
                    "target_simple_s": 2,
                    "target_complex_s": 15,
                    "status": status,
                    "available": True
                }
            elif response.status_code == 404:
                # User not found - this is expected if no sample data
                return {
                    "status": "error", 
                    "error": "User not found (404) - generate sample data first", 
                    "available": False,
                    "response_time_s": None,
                    "suggestion": "Run: python3 scripts/generate_sample_data.py"
                }
            else:
                return {
                    "status": "error", 
                    "error": f"HTTP {response.status_code}", 
                    "available": False,
                    "response_time_s": None
                }
        except Exception as e:
            logger.error(f"Recommendation KPI check failed: {e}")
            return {
                "status": "error", 
                "error": str(e), 
                "available": False,
                "response_time_s": None
            }

    async def _get_cache_hit_rate_kpi(self) -> Dict[str, Any]:
        """キャッシュヒット率 KPI: > 80%"""
        try:
            client = await self.get_http_client()
            response = await client.get(f"http://localhost:8080/api/v1/analytics-sync/cache-stats")
            
            if response.status_code == 200:
                data = response.json()
                cache_stats = data.get("cache_stats", {})
                hit_rate = cache_stats.get("cache_hit_rate", "0%")
                
                # Handle both string and numeric formats
                if isinstance(hit_rate, str):
                    hit_rate_percent = float(hit_rate.replace("%", "")) if hit_rate.replace("%", "").replace(".", "").isdigit() else 0
                else:
                    hit_rate_percent = hit_rate * 100 if hit_rate <= 1 else hit_rate
                
                return {
                    "hit_rate_percent": round(hit_rate_percent, 1),
                    "target_percent": 80,
                    "total_cached_users": cache_stats.get("total_cached_users", 0),
                    "status": "excellent" if hit_rate_percent >= 80 else "good" if hit_rate_percent >= 60 else "poor",
                    "available": True
                }
            else:
                return {"status": "error", "error": f"HTTP {response.status_code}", "available": False}
        except Exception as e:
            return {"status": "error", "error": str(e), "available": False}

    async def _get_sync_performance_kpi(self) -> Dict[str, Any]:
        """data同期パフォーマンス KPI: < 30秒/バッチ, success率 > 95%"""
        try:
            client = await self.get_http_client()
            response = await client.get(f"http://localhost:8080/api/v1/analytics-sync/status")
            
            if response.status_code == 200:
                data = response.json()
                sync_services = data.get("sync_services", {})
                
                sync_enabled = sync_services.get("sync_enabled", False)
                initial_sync_enabled = sync_services.get("initial_sync_enabled", False)
                healthy = sync_services.get("health", {}).get("healthy", False)
                
                return {
                    "sync_enabled": sync_enabled,
                    "initial_sync_enabled": initial_sync_enabled,
                    "healthy": healthy,
                    "target_time_s": 30,
                    "target_success_rate": 95,
                    "status": "excellent" if (sync_enabled and healthy) else "good" if sync_enabled else "poor",
                    "available": True
                }
            else:
                return {"status": "error", "error": f"HTTP {response.status_code}", "available": False}
        except Exception as e:
            return {"status": "error", "error": str(e), "available": False}

    async def _get_availability_kpi(self) -> Dict[str, Any]:
        """アプリケーションavailable性 KPI: > 99.5%"""
        try:
            # コアサービス ステータス チェック
            core_services = []
            service_checks = {
                'health': False,
                'recommendations': False,
                'sync_status': False
            }
            
            client = await self.get_http_client()
            
            # ヘルスチェック
            try:
                health_response = await client.get(f"http://localhost:8080/api/v1/health")
                service_checks['health'] = health_response.status_code == 200
                core_services.append(('ヘルスチェック', service_checks['health']))
            except:
                service_checks['health'] = False
                core_services.append(('ヘルスチェック', False))
            
            # recommendationサービス チェック（コアビジネス機能）
            try:
                rec_response = await client.get(f"http://localhost:8080/api/v1/recommendations-firestore-primary/analyze/1001")
                service_checks['recommendations'] = rec_response.status_code == 200
                core_services.append(('推奨サービス', service_checks['recommendations']))
            except:
                service_checks['recommendations'] = False
                core_services.append(('推奨サービス', False))
            
            # 同期ステータスAPI チェック
            try:
                sync_response = await client.get(f"http://localhost:8080/api/v1/analytics-sync/status")
                service_checks['sync_status'] = sync_response.status_code == 200
                core_services.append(('同期ステータス', service_checks['sync_status']))
            except:
                service_checks['sync_status'] = False
                core_services.append(('同期ステータス', False))
            
            # available性パーセンテージ 計算
            available_count = sum(check for check in service_checks.values())
            total_count = len(service_checks)
            availability_percent = (available_count / total_count) * 100
            
            return {
                "availability_percent": round(availability_percent, 1),
                "target_percent": 99.5,
                "service_checks": service_checks,
                "available_services": available_count,
                "total_services": total_count,
                "core_services": core_services,
                "status": "excellent" if availability_percent >= 99.5 else "good" if availability_percent >= 80 else "poor",
                "available": True
            }
        except Exception as e:
            return {"status": "error", "error": str(e), "available": False}

    def _calculate_business_kpi_status(self, kpis: Dict[str, Any]) -> Dict[str, Any]:
        """全体 なビジネスKPIステータス 計算"""
        excellent_count = 0
        good_count = 0
        poor_count = 0
        error_count = 0
        total_kpis = 0
        
        for kpi_name, kpi_data in kpis.items():
            if kpi_name == "overall":
                continue
                
            if isinstance(kpi_data, dict) and "status" in kpi_data:
                total_kpis += 1
                status = kpi_data["status"]
                if status == "excellent":
                    excellent_count += 1
                elif status == "good":
                    good_count += 1
                elif status == "poor":
                    poor_count += 1
                elif status == "error":
                    error_count += 1
        
        # 全体 なステータス 計算
        if error_count > 0:
            overall_status = "critical"
            message = f"{error_count}個 KPIチェック failed"
        elif poor_count > good_count + excellent_count:
            overall_status = "poor"
            message = f"{poor_count}個 KPIパフォーマンス 不良"
        elif excellent_count >= good_count:
            overall_status = "excellent"
            message = f"{excellent_count}個 KPIパフォーマンス 優秀"
        else:
            overall_status = "good"
            message = f"{good_count}個 KPIパフォーマンス 良好"
        
        return {
            "status": overall_status,
            "message": message,
            "excellent_count": excellent_count,
            "good_count": good_count,
            "poor_count": poor_count,
            "error_count": error_count,
            "total_count": total_kpis
        }

    async def perform_deep_checks(self) -> Dict[str, Any]:
        """
        ビジネスロジック テスト including、包括 なシステムヘルスチェック execute
        これ 通常 モニタリングよりも詳細 、リアルタイムストリーム  なくオンデマンド 呼び出す必要 あります
        """
        try:
            logger.info("詳細なシステムチェック 開始します")
            
            # 詳細チェック 基礎 してすべて KPIdata 取得
            business_kpis = await self._get_business_kpis()
            
            # 詳細チェック 結果 build
            results = {
                "timestamp": datetime.now().isoformat(),
                "health_check": {
                    "status": business_kpis.get("health_check", {}).get("status", "error"),
                    "response_time_ms": business_kpis.get("health_check", {}).get("response_time_ms", 0),
                    "available": business_kpis.get("health_check", {}).get("available", False)
                },
                "api_performance": {
                    "status": business_kpis.get("recommendation_api", {}).get("status", "error"),
                    "response_time_s": business_kpis.get("recommendation_api", {}).get("response_time_s", 0),
                    "category": business_kpis.get("recommendation_api", {}).get("category", "不明"),
                    "available": business_kpis.get("recommendation_api", {}).get("available", False)
                },
                "sync_status": {
                    "sync_enabled": business_kpis.get("sync_performance", {}).get("sync_enabled", False),
                    "healthy": business_kpis.get("sync_performance", {}).get("healthy", False),
                    "status": business_kpis.get("sync_performance", {}).get("status", "error"),
                    "available": business_kpis.get("sync_performance", {}).get("available", False)
                },
                "cache_performance": {
                    "hit_rate_percent": business_kpis.get("cache_hit_rate", {}).get("hit_rate_percent", 0),
                    "status": business_kpis.get("cache_hit_rate", {}).get("status", "error"),
                    "available": business_kpis.get("cache_hit_rate", {}).get("available", False)
                },
                "availability": {
                    "availability_percent": business_kpis.get("availability", {}).get("availability_percent", 0),
                    "available_services": business_kpis.get("availability", {}).get("available_services", 0),
                    "total_services": business_kpis.get("availability", {}).get("total_services", 0),
                    "status": business_kpis.get("availability", {}).get("status", "error")
                }
            }
            
            # 全体 な評価 generate
            results["overall_assessment"] = self._assess_deep_check_results(results)
            
            logger.info(f"詳細チェック完了、全体ステータス: {results['overall_assessment']['status']}")
            return results
            
        except Exception as e:
            logger.error(f"詳細チェック execute failed: {e}")
            return {
                "timestamp": datetime.now().isoformat(),
                "error": "詳細チェックexecutefailed",
                "details": str(e),
                "overall_assessment": {
                    "status": "critical",
                    "message": "詳細チェックシステム障害",
                    "issues": ["詳細チェックexecute異常"]
                }
            }

    def _assess_deep_check_results(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """詳細チェック 結果 評価し、全体 な状況 provide"""
        issues = []
        warnings = []
        
        # ヘルスチェック
        if results["health_check"]["status"] != "excellent":
            if results["health_check"]["response_time_ms"] > 100:
                issues.append("ヘルスチェック応答時間 過長")
            elif results["health_check"]["response_time_ms"] > 50:
                warnings.append("ヘルスチェック応答時間 やや高い")
        
        # APIパフォーマンス チェック
        if not results["api_performance"]["available"]:
            issues.append("推奨API 利用不可")
        elif results["api_performance"]["status"] == "poor":
            issues.append("推奨API応答時間 過長")
            
        # 同期ステータス チェック
        if not results["sync_status"]["sync_enabled"]:
            issues.append("data同期 無効")
        elif not results["sync_status"]["healthy"]:
            warnings.append("data同期サービス 不health")
            
        # キャッシュパフォーマンス チェック
        if results["cache_performance"]["hit_rate_percent"] < 50:
            issues.append("キャッシュヒット率 過低")
        elif results["cache_performance"]["hit_rate_percent"] < 80:
            warnings.append("キャッシュヒット率 低い")
            
        # available性 チェック
        if results["availability"]["availability_percent"] < 99:
            issues.append("アプリavailable性 基準未達")
        elif results["availability"]["availability_percent"] < 99.5:
            warnings.append("アプリavailable性 目標 若干下回る")
        
        # 全体 なステータス 決定
        if len(issues) > 0:
            if len(issues) >= 3:
                status = "critical"
                message = f"{len(issues)}個 深刻な問題 発見、即座 対処 必要"
            else:
                status = "poor"
                message = f"{len(issues)}個 問題 発見、note 必要"
        elif len(warnings) > 2:
            status = "warning"
            message = f"システム 基本  normally、{len(warnings)}個 warn項目あり"
        elif len(warnings) > 0:
            status = "good"
            message = f"システム 良好 動作、{len(warnings)}個 軽微なwarnあり"
        else:
            status = "excellent"
            message = "全システムチェック通過、動作状態 優秀"
            
        return {
            "status": status,
            "message": message,
            "issues": issues,
            "warnings": warnings,
            "total_issues": len(issues),
            "total_warnings": len(warnings),
            "recommendations": self._generate_recommendations(issues, warnings)
        }

    def _generate_recommendations(self, issues: List[str], warnings: List[str]) -> List[str]:
        """チェック結果 based on改善提案 generate"""
        recommendations = []
        
        if "ヘルスチェック応答時間 過長" in issues:
            recommendations.append("アプリ起動時間 依存関係 読み込み 最適化")
        if "推奨API 利用不可" in issues:
            recommendations.append("推奨サービス設定 依存関係 確認")
        if "data同期 無効" in issues:
            recommendations.append("data同期サービス 開始")
        if "キャッシュヒット率 過低" in issues:
            recommendations.append("キャッシュ戦略 data分散 確認")
        if "アプリavailable性 基準未達" in issues:
            recommendations.append("サービス監視 障害復旧メカニズム 確認")
            
        if not recommendations:
            recommendations.append("システム 良好 動作、現在 状態 維持")
            
        return recommendations


# グローバルなシングルトンインスタンス、HTTP接続プール 再作成 回避
_monitoring_service_instance = None

def get_monitoring_service() -> MonitoringService:
    """Dependency injector for MonitoringService - リソースリーク 避けるfor シングルトンパターン use"""
    global _monitoring_service_instance
    if _monitoring_service_instance is None:
        _monitoring_service_instance = MonitoringService()
    return _monitoring_service_instance
