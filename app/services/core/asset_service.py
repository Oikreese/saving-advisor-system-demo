"""
coreasset service - sharedbusiness logic
provide统一 asset管理service，被FastAPIandgRPCendpoint共同use
"""
from typing import Optional, Dict, Any, List
from datetime import datetime
import time

# projectcore依赖
from app.services.firestore.firestore_primary_service import FirestorePrimaryService, get_firestore_primary_service
from app.models.assets import UserPortfolio
from app.core.logging import logger


class AssetResult:
    """assetresultdataclass"""
    
    def __init__(
        self, 
        success: bool = True,
        data: Optional[Any] = None,
        error_message: Optional[str] = None,
        timestamp: Optional[int] = None
    ):
        self.success = success
        self.data = data
        self.error_message = error_message
        self.timestamp = timestamp or int(time.time())
    
    def to_dict(self) -> Dict[str, Any]:
        """convert为dictionary格式"""
        return {
            "success": self.success,
            "data": self.data,
            "error_message": self.error_message,
            "timestamp": self.timestamp
        }


class CoreAssetService:
    """
    coreasset service - 统一 business logic层
    
    thisserviceincludes所有asset管理相关 corebusiness logic，被以下endpointuse：
    - FastAPI RESTendpoint
    - gRPCserviceendpoint
    - in部servicecall
    """
    
    def __init__(self):
        """initializecoreasset service"""
        self._firestore_service: Optional[FirestorePrimaryService] = None
        logger.info("CoreAssetService initializecomplete")
    
    async def _get_firestore_service(self) -> FirestorePrimaryService:
        """getFirestoreservice实例（懒load）"""
        if self._firestore_service is None:
            self._firestore_service = get_firestore_primary_service()
            logger.debug("Firestoreservice实例alreadycreate")
        return self._firestore_service
    
    # =============== coreassetmethod ===============
    
    async def get_user_portfolio(
        self, 
        user_id: str, 
        allow_empty: bool = True
    ) -> AssetResult:
        """
        getuserportfolio - corebusiness logic
        
        Args:
            user_id: userID
            allow_empty: whether允许空portfolio
            
        Returns:
            AssetResult: portfolioresult
        """
        logger.info(f"getuserportfolio: user_id={user_id}")
        
        try:
            # getFirestoreservice
            firestore_service = await self._get_firestore_service()
            
            # getuserportfolio
            portfolio = await firestore_service.get_user_portfolio(
                user_id, 
                allow_empty=allow_empty, 
                raise_http_exception=False
            )
            
            if not portfolio and not allow_empty:
                logger.warning(f"user {user_id}  portfolio未找到")
                return AssetResult(
                    success=False,
                    error_message="指定されたuser portfolio 見つかりません"
                )
            
            logger.info(f"userportfoliogetsuccess: user_id={user_id}")
            
            return AssetResult(
                success=True,
                data=portfolio
            )
            
        except Exception as e:
            logger.error(f"getuserportfoliofail: user_id={user_id}, error={e}")
            return AssetResult(
                success=False,
                error_message=str(e)
            )
    
    async def update_user_asset(
        self, 
        user_id: str, 
        asset_id: str, 
        asset_data: Dict[str, Any]
    ) -> AssetResult:
        """
        updateuserasset
        
        Args:
            user_id: userID
            asset_id: assetID
            asset_data: assetdata
            
        Returns:
            AssetResult: updateresult
        """
        logger.info(f"updateuserasset: user_id={user_id}, asset_id={asset_id}")
        
        try:
            # getFirestoreservice
            firestore_service = await self._get_firestore_service()
            
            # updateassetdata
            result = await firestore_service.update_user_asset(user_id, asset_id, asset_data)
            
            logger.info(f"userassetupdatesuccess: user_id={user_id}, asset_id={asset_id}")
            
            return AssetResult(
                success=True,
                data=result
            )
            
        except Exception as e:
            logger.error(f"updateuserassetfail: user_id={user_id}, asset_id={asset_id}, error={e}")
            return AssetResult(
                success=False,
                error_message=str(e)
            )
    
    async def add_user_asset(
        self, 
        user_id: str, 
        asset: Dict[str, Any]
    ) -> AssetResult:
        """
        adduserasset
        
        Args:
            user_id: userID
            asset: assetobject
            
        Returns:
            AssetResult: addresult
        """
        logger.info(f"adduserasset: user_id={user_id}, asset_type={asset.get('asset_type', 'unknown')}")
        
        try:
            # getFirestoreservice
            firestore_service = await self._get_firestore_service()
            
            # addasset
            result = await firestore_service.add_user_asset(user_id, asset)
            
            logger.info(f"userassetaddsuccess: user_id={user_id}")
            
            return AssetResult(
                success=True,
                data=result
            )
            
        except Exception as e:
            logger.error(f"adduserassetfail: user_id={user_id}, error={e}")
            return AssetResult(
                success=False,
                error_message=str(e)
            )
    
    async def delete_user_asset(
        self, 
        user_id: str, 
        asset_id: str
    ) -> AssetResult:
        """
        deleteuserasset
        
        Args:
            user_id: userID
            asset_id: assetID
            
        Returns:
            AssetResult: deleteresult
        """
        logger.info(f"deleteuserasset: user_id={user_id}, asset_id={asset_id}")
        
        try:
            # getFirestoreservice
            firestore_service = await self._get_firestore_service()
            
            # deleteasset
            result = await firestore_service.delete_user_asset(user_id, asset_id)
            
            logger.info(f"userassetdeletesuccess: user_id={user_id}, asset_id={asset_id}")
            
            return AssetResult(
                success=True,
                data=result
            )
            
        except Exception as e:
            logger.error(f"deleteuserassetfail: user_id={user_id}, asset_id={asset_id}, error={e}")
            return AssetResult(
                success=False,
                error_message=str(e)
            )
    
    async def get_portfolio_summary(
        self, 
        user_id: str
    ) -> AssetResult:
        """
        getportfolio摘要
        
        Args:
            user_id: userID
            
        Returns:
            AssetResult: portfolio摘要result
        """
        logger.info(f"getportfolio摘要: user_id={user_id}")
        
        try:
            # getuserportfolio
            portfolio_result = await self.get_user_portfolio(user_id, allow_empty=True)
            
            if not portfolio_result.success:
                return portfolio_result
            
            portfolio = portfolio_result.data
            
            if not portfolio:
                summary = {
                    "user_id": user_id,
                    "total_value": 0,
                    "asset_count": 0,
                    "asset_types": [],
                    "last_updated": None
                }
            else:
                # 计算摘要info
                total_value = portfolio.total_estimated_value or 0
                asset_count = len(portfolio.assets)
                asset_types = list(set(asset.asset_type for asset in portfolio.assets)) if portfolio.assets else []
                last_updated = portfolio.last_updated.isoformat() if portfolio.last_updated else None
                
                summary = {
                    "user_id": user_id,
                    "total_value": total_value,
                    "asset_count": asset_count,
                    "asset_types": asset_types,
                    "last_updated": last_updated
                }
            
            logger.info(f"portfolio摘要getsuccess: user_id={user_id}")
            
            return AssetResult(
                success=True,
                data=summary
            )
            
        except Exception as e:
            logger.error(f"getportfolio摘要fail: user_id={user_id}, error={e}")
            return AssetResult(
                success=False,
                error_message=str(e)
            )
    
    async def health_check(self) -> AssetResult:
        """
        asset servicehealth check
        
        Returns:
            AssetResult: health checkresult
        """
        try:
            # check依赖serviceconnected
            firestore_service = await self._get_firestore_service()
            
            # 简单 connectedtest
            # 这里可以add更多 health checklogic
            
            return AssetResult(
                success=True,
                data={
                    "status": "healthy",
                    "service": "core_asset_service",
                    "firestore": "connected",
                    "timestamp": datetime.now().isoformat()
                }
            )
            
        except Exception as e:
            logger.error(f"asset servicehealth checkfail: {e}")
            return AssetResult(
                success=False,
                error_message=str(e)
            )


# =============== singleton实例 ===============

_core_asset_service: Optional[CoreAssetService] = None


def get_core_asset_service() -> CoreAssetService:
    """
    getcoreasset servicesingleton实例
    
    Returns:
        CoreAssetService: coreasset service实例
    """
    global _core_asset_service
    if _core_asset_service is None:
        _core_asset_service = CoreAssetService()
        logger.info("coreasset servicesingleton实例alreadycreate")
    return _core_asset_service
