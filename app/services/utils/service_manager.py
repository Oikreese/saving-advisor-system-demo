"""
統一サービスマネージャー - sync_starter.py と analytics_starter.py の重複コードを削除

機能:
1. 統一的なプロセス管理とクリーンアップロジック
2. 統一的なCeleryサービス起動ロジック  
3. 統一的なエラー処理とログ記録
4. 設定可能なサービスタイプサポート
"""

import asyncio
import subprocess
import time
import logging
import os
import signal
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass
from datetime import datetime

from app.core.logging import logger
from app.core.config import settings


@dataclass
class ServiceConfig:
    """サービス設定"""
    name: str                    # サービス名
    task_module: str            # Celeryタスクモジュール
    worker_queue: str           # Workerキュー名
    worker_concurrency: int     # Worker並行数
    worker_pidfile: str         # Worker PIDファイルパス
    beat_pidfile: str          # Beat PIDファイルパス
    worker_logfile: str        # Workerログファイルパス
    beat_logfile: str          # Beatログファイルパス
    loglevel: str = 'info'     # ログレベル
    enable_config_key: str = None  # 設定キー名


class UnifiedServiceManager:
    """統一サービスマネージャー"""
    
    # 予め定義されたサービス設定
    SERVICE_CONFIGS = {
        'analytics_sync': ServiceConfig(
            name='分析同期サービス',
            task_module='app.tasks.analytics_sync_tasks',
            worker_queue='analytics_sync',
            worker_concurrency=2,
            worker_pidfile='/tmp/sync_worker.pid',
            beat_pidfile='/tmp/sync_beat.pid', 
            worker_logfile='/tmp/sync_worker.log',
            beat_logfile='/tmp/sync_beat.log',
            loglevel='info',
            enable_config_key='ENABLE_ANALYTICS_SYNC'
        ),
        # NOTE: BigQuery Analytics已被批处理系统替代
        # 使用 app.tasks.batch_tasks 和 scripts/batch_jobs/
        'batch_analytics': ServiceConfig(
            name='批处理分析服务',
            task_module='app.tasks.batch_tasks',
            worker_queue='batch_jobs',
            worker_concurrency=4,
            worker_pidfile='/tmp/batch_worker.pid',
            beat_pidfile='/tmp/batch_beat.pid',
            worker_logfile='logs/celery_worker.log',
            beat_logfile='logs/celery_beat.log',
            loglevel='info',
            enable_config_key='ENABLE_ANALYTICS'
        )
    }
    
    def __init__(self):
        self.project_root = Path(__file__).parent.parent.parent.parent
        self.started_services: Dict[str, Dict[str, Optional[int]]] = {}
        
    async def start_service(self, service_type: str, **kwargs) -> Dict[str, Any]:
        """
        指定されたタイプのサービスを起動
        
        Args:
            service_type: サービスタイプ ('analytics_sync' または 'batch_analytics')
            **kwargs: オプション設定オーバーライド
        """
        if service_type not in self.SERVICE_CONFIGS:
            raise ValueError(f"サポートされていないサービスタイプ: {service_type}")
            
        config = self.SERVICE_CONFIGS[service_type]
        
        # サービスが有効かどうかをチェック
        if config.enable_config_key:
            enabled = getattr(settings, config.enable_config_key, True)
            if not enabled:
                logger.info(f"📊 {config.name}は無効化されています")
                return {'status': 'disabled', 'message': f'{config.name}は設定で無効化されています'}
        
        # 既にプロセスが実行中かどうかをチェック (メモリ記録のみではなく)
        current_status = await self.get_service_status(service_type)
        if current_status.get('status') == 'running':
            logger.info(f"📊 {config.name}はすでに実行中です")
            return {'status': 'already_running', 'message': f'{config.name}はすでに実行中です', 'current_status': current_status}
        elif current_status.get('status') == 'partial':
            logger.warning(f"⚠️ {config.name}の一部のコンポーネントが実行中のため、クリーンアップ後に再起動します。")
            # 部分実行プロセスをクリーンアップ
            await self._cleanup_partial_processes(config, current_status)
            
        logger.info(f"🔄 {config.name}を起動中...")
        
        try:
            # 1. 古いプロセスとpidfileをクリーンアップ
            await self._cleanup_stale_processes(config)
            
            # 2. Workerプロセスを起動
            worker_result = await self._start_worker(config)
            if not worker_result['success']:
                return worker_result
                
            # 3. Beatスケジューラを起動
            beat_result = await self._start_beat(config)
            if not beat_result['success']:
                return beat_result
            
            # 4. 起動状態を記録
            self.started_services[service_type] = {
                'worker_pid': worker_result.get('pid'),
                'beat_pid': beat_result.get('pid'),
                'config': config
            }
            
            logger.info(f"✅ {config.name}の起動に成功しました (Worker PID: {worker_result.get('pid')}, Beat PID: {beat_result.get('pid')})")
            
            return {
                'status': 'success',
                'service': config.name,
                'worker_pid': worker_result.get('pid'),
                'beat_pid': beat_result.get('pid'),
                'message': f'{config.name}の起動に成功しました'
            }
            
        except Exception as e:
            logger.error(f"{config.name}の起動に失敗しました: {e}")
            return {
                'status': 'error',
                'service': config.name,
                'error': str(e),
                'message': f'{config.name}の起動中にエラーが発生しました'
            }
    
    async def stop_service(self, service_type: str) -> Dict[str, Any]:
        """サービスを停止"""
        if service_type not in self.started_services:
            return {'status': 'not_running', 'message': f'サービス {service_type} は実行されていません'}
            
        service_info = self.started_services[service_type]
        config = service_info['config']
        
        logger.info(f"🔄 {config.name}を停止中...")
        
        stopped_processes = []
        
        # Workerを停止
        if service_info.get('worker_pid'):
            try:
                os.kill(service_info['worker_pid'], signal.SIGTERM)
                stopped_processes.append(f"Worker (PID: {service_info['worker_pid']})")
                logger.info(f"{config.name} Workerプロセスは停止しました")
            except ProcessLookupError:
                logger.info(f"{config.name} Workerプロセスは存在しません")
            except Exception as e:
                logger.warning(f"{config.name} Workerの停止に失敗しました: {e}")
        
        # Beatを停止
        if service_info.get('beat_pid'):
            try:
                os.kill(service_info['beat_pid'], signal.SIGTERM)
                stopped_processes.append(f"Beat (PID: {service_info['beat_pid']})")
                logger.info(f"{config.name} Beatプロセスは停止しました")
            except ProcessLookupError:
                logger.info(f"{config.name} Beatプロセスは存在しません")
            except Exception as e:
                logger.warning(f"{config.name} Beatの停止に失敗しました: {e}")
        
        # PIDファイルをクリーンアップ
        for pid_file in [config.worker_pidfile, config.beat_pidfile]:
            try:
                if os.path.exists(pid_file):
                    os.remove(pid_file)
            except Exception as e:
                logger.warning(f"PIDファイルのクリーンアップに失敗 {pid_file}: {e}")
        
        # 起動済みサービスから削除
        del self.started_services[service_type]
        
        logger.info(f"✅ {config.name}は正常に停止しました")
        
        return {
            'status': 'success',
            'service': config.name,
            'stopped_processes': stopped_processes,
            'message': f'{config.name}は正常に停止しました'
        }
    
    async def get_service_status(self, service_type: str) -> Dict[str, Any]:
        """サービスの状態を取得 - 実際に実行されているプロセスをチェックします"""
        if service_type not in self.SERVICE_CONFIGS:
            return {'status': 'unknown', 'message': '不明なサービスタイプ'}
            
        config = self.SERVICE_CONFIGS[service_type]
        
        # まず、実際に実行されているCeleryプロセスをチェック
        running_processes = await self._get_running_celery_processes(config)
        
        worker_running = len(running_processes['workers']) > 0
        beat_running = len(running_processes['beats']) > 0
        
        # メモリに記録がある場合、PIDが一致するかどうかを確認
        if service_type in self.started_services:
            service_info = self.started_services[service_type]
            stored_worker_pid = service_info.get('worker_pid')
            stored_beat_pid = service_info.get('beat_pid')
            
            # 保存されたPIDがまだ実行中かどうかをチェック
            stored_worker_running = self._check_process_running(stored_worker_pid)
            stored_beat_running = self._check_process_running(stored_beat_pid)
            
            return {
                'status': 'running' if (worker_running and beat_running) else 'partial' if (worker_running or beat_running) else 'stopped',
                'service': config.name,
                'worker_running': worker_running,
                'beat_running': beat_running,
                'stored_worker_pid': stored_worker_pid,
                'stored_beat_pid': stored_beat_pid,
                'stored_worker_running': stored_worker_running,
                'stored_beat_running': stored_beat_running,
                'actual_processes': running_processes,
                'message': f'{config.name}の状態チェックが完了しました'
            }
        else:
            # メモリに記録がない場合、実際のプロセスのみを基に
            return {
                'status': 'running' if (worker_running and beat_running) else 'partial' if (worker_running or beat_running) else 'stopped',
                'service': config.name,
                'worker_running': worker_running,
                'beat_running': beat_running,
                'worker_pid': running_processes['workers'][0] if running_processes['workers'] else None,
                'beat_pid': running_processes['beats'][0] if running_processes['beats'] else None,
                'actual_processes': running_processes,
                'message': f'{config.name}の状態チェックが完了しました (実際のプロセスに基づく)'
            }
    
    # ==================== 内部メソッド ====================
    
    async def _get_running_celery_processes(self, config: ServiceConfig) -> Dict[str, List[int]]:
        """実際に実行されているCeleryプロセスを取得"""
        import subprocess
        
        try:
            # 関連するCeleryプロセスを検索
            result = await asyncio.create_subprocess_shell(
                f"ps aux | grep 'celery.*{config.task_module}' | grep -v grep",
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            stdout, stderr = await result.communicate()
            
            if result.returncode != 0:
                return {'workers': [], 'beats': []}
            
            processes = stdout.decode().strip().split('\n')
            workers = []
            beats = []
            
            for process_line in processes:
                if not process_line.strip():
                    continue
                    
                parts = process_line.strip().split()
                if len(parts) < 2:
                    continue
                    
                pid = int(parts[1])
                
                if 'worker' in process_line and f'--queues={config.worker_queue}' in process_line:
                    workers.append(pid)
                elif 'beat' in process_line:
                    beats.append(pid)
            
            return {'workers': workers, 'beats': beats}
            
        except Exception as e:
            logger.warning(f"実行プロセスの取得に失敗しました: {e}")
            return {'workers': [], 'beats': []}
    
    async def _cleanup_partial_processes(self, config: ServiceConfig, status: Dict[str, Any]):
        """部分実行プロセスをクリーンアップ"""
        try:
            running_processes = status.get('actual_processes', {'workers': [], 'beats': []})
            
            # 関連するすべてのプロセスを終了
            all_pids = running_processes['workers'] + running_processes['beats']
            for pid in all_pids:
                try:
                    os.kill(pid, signal.SIGTERM)
                    logger.info(f"プロセス PID: {pid}を終了")
                except ProcessLookupError:
                    pass  # プロセスは既に存在しない
                except Exception as e:
                    logger.warning(f"プロセス {pid} の終了に失敗: {e}")
            
            # プロセスが終了するのを待つ
            await asyncio.sleep(2)
            
            # まだ実行中のプロセスを強制終了
            for pid in all_pids:
                try:
                    os.kill(pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass  # プロセスは既に終了
                except Exception as e:
                    logger.warning(f"強制終了プロセス {pid} に失敗: {e}")
            
            logger.info(f"部分実行プロセス {len(all_pids)} 個をクリーンアップしました")
            
        except Exception as e:
            logger.error(f"部分プロセスのクリーンアップに失敗しました: {e}")
    
    async def _cleanup_stale_processes(self, config: ServiceConfig):
        """古いプロセスとpidfileをクリーンアップ"""
        pid_files = {
            config.worker_pidfile: f'{config.name} Worker',
            config.beat_pidfile: f'{config.name} Beat'
        }
        
        for pid_file, process_name in pid_files.items():
            if os.path.exists(pid_file):
                try:
                    with open(pid_file, 'r') as f:
                        pid = int(f.read().strip())
                    
                    # プロセスがまだ実行中かどうかをチェック
                    try:
                        # 信号0を送信してプロセスが存在するかどうかを確認（プロセスを終了しない）
                        os.kill(pid, 0)
                        logger.warning(f"{process_name} プロセス (PID: {pid}) はまだ実行中です。停止を試みます...")
                        
                        # 優雅に停止を試みる
                        os.kill(pid, signal.SIGTERM)
                        time.sleep(2)
                        
                        # 停止されたかどうかを確認
                        try:
                            os.kill(pid, 0)
                            # まだ実行中の場合、強制停止
                            logger.warning(f"{process_name} プロセス (PID: {pid}) はSIGTERMに応答しませんでした。強制停止を試みます...")
                            os.kill(pid, signal.SIGKILL)
                            time.sleep(1)
                        except ProcessLookupError:
                            # プロセスは停止された
                            logger.info(f"{process_name} プロセス (PID: {pid}) は正常に停止されました")
                            
                    except ProcessLookupError:
                        # プロセスが存在しない場合、pidfileのみをクリーンアップ
                        logger.info(f"{process_name} プロセス (PID: {pid}) は存在しません。pidfileをクリーンアップします")
                    
                    # pidfileをクリーンアップ
                    os.remove(pid_file)
                    logger.info(f"古いpidfileをクリーンアップしました: {pid_file}")
                    
                except (ValueError, FileNotFoundError) as e:
                    logger.warning(f"pidfile {pid_file} のクリーンアップ中にエラーが発生しました: {e}")
                    # 破損したpidfileを削除しようとする
                    try:
                        os.remove(pid_file)
                    except:
                        pass
    
    async def _start_worker(self, config: ServiceConfig) -> Dict[str, Any]:
        """Workerプロセスを起動"""
        worker_cmd = [
            'python', '-m', 'celery',
            '-A', config.task_module,
            'worker',
            f'--loglevel={config.loglevel}',
            f'--queues={config.worker_queue}',
            f'--concurrency={config.worker_concurrency}',
            '--detach',
            f'--pidfile={config.worker_pidfile}',
            f'--logfile={config.worker_logfile}'
        ]
        
        logger.info(f"{config.name} Workerを起動中...")
        result = subprocess.run(worker_cmd, cwd=self.project_root, capture_output=True, text=True)
        
        if result.returncode != 0:
            error_msg = f"{config.name} Workerの起動に失敗: {result.stderr}"
            logger.error(error_msg)
            return {'success': False, 'error': error_msg}
        
        # pidfileが生成されるのを待つ
        await asyncio.sleep(2)
        
        # PIDを読み取る
        try:
            with open(config.worker_pidfile, 'r') as f:
                pid = int(f.read().strip())
            logger.info(f"{config.name} Workerの起動に成功 (PID: {pid})")
            return {'success': True, 'pid': pid}
        except Exception as e:
            return {'success': False, 'error': f'Worker PIDを読み取れません: {e}'}
    
    async def _start_beat(self, config: ServiceConfig) -> Dict[str, Any]:
        """Beatスケジューラを起動"""
        beat_cmd = [
            'python', '-m', 'celery',
            '-A', config.task_module,
            'beat',
            f'--loglevel={config.loglevel}',
            '--detach',
            f'--pidfile={config.beat_pidfile}',
            f'--logfile={config.beat_logfile}'
        ]
        
        logger.info(f"{config.name} Beatスケジューラを起動中...")
        result = subprocess.run(beat_cmd, cwd=self.project_root, capture_output=True, text=True)
        
        if result.returncode != 0:
            error_msg = f"{config.name} Beatスケジューラの起動に失敗: {result.stderr}"
            logger.error(error_msg)
            return {'success': False, 'error': error_msg}
        
        # pidfileが生成されるのを待つ
        await asyncio.sleep(2)
        
        # PIDを読み取る
        try:
            with open(config.beat_pidfile, 'r') as f:
                pid = int(f.read().strip())
            logger.info(f"{config.name} Beatスケジューラの起動に成功 (PID: {pid})")
            return {'success': True, 'pid': pid}
        except Exception as e:
            return {'success': False, 'error': f'Beat PIDを読み取れません: {e}'}
    
    def _check_process_running(self, pid: Optional[int]) -> bool:
        """プロセスが実行中かどうかをチェック"""
        if not pid:
            return False
            
        try:
            os.kill(pid, 0)
            return True
        except ProcessLookupError:
            return False
        except PermissionError:
            # プロセスは存在するが、シグナルを送信する権限がない
            return True


# グローバルインスタンス
unified_service_manager = UnifiedServiceManager()


# ==================== 互換性関数 ====================

async def start_sync_services() -> Dict[str, Any]:
    """分析同期サービスを起動 (旧 sync_starter.py互換)"""
    return await unified_service_manager.start_service('analytics_sync')


async def start_analytics_services() -> Dict[str, Any]:
    """批处理分析サービスを起動 (替代 BigQuery Analytics)"""
    return await unified_service_manager.start_service('batch_analytics')


async def stop_sync_services() -> Dict[str, Any]:
    """分析同期サービスを停止"""
    return await unified_service_manager.stop_service('analytics_sync')


async def stop_analytics_services() -> Dict[str, Any]:
    """批处理分析サービスを停止"""
    return await unified_service_manager.stop_service('batch_analytics')
