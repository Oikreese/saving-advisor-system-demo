"""
BigQuery增强客户端兼容层
"""
from . import EnhancedBigQueryClient, get_enhanced_bigquery_client

# 重新导出以保持兼容性
__all__ = ['EnhancedBigQueryClient', 'get_enhanced_bigquery_client']
