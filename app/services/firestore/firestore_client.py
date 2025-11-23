"""
Firestore客户端兼容层
"""
from . import FirestoreClient, get_firestore_client

# 重新导出以保持兼容性
__all__ = ['FirestoreClient', 'get_firestore_client']
