"""
Firestore 兼容服务

该包保留原始导入路径，同时将实现委托给
`firestore_primary_service.py` 文件中的开放源码版本。
"""

from .firestore_primary_service import FirestorePrimaryService, get_firestore_primary_service

__all__ = ["FirestorePrimaryService", "get_firestore_primary_service"]
