"""
优化洞察服务兼容层
"""
from . import OptimizedInsightsService, get_optimized_insights_service

# 重新导出以保持兼容性
__all__ = ['OptimizedInsightsService', 'get_optimized_insights_service']
