from fastapi import APIRouter, Depends, HTTPException
from typing import Dict
from app.models.assets import UserPortfolio
from app.services.firestore.firestore_primary_service import get_firestore_primary_service, FirestorePrimaryService
from app.core.logging import logger

router = APIRouter()

@router.get("/portfolio/{user_id}", response_model=Dict[str, UserPortfolio])
async def get_user_portfolio(user_id: str, firestore_service: FirestorePrimaryService = Depends(get_firestore_primary_service)):
    """
    ユーザーのポートフォリオを取得
    
    Args:
        user_id: ユーザーID
        
    Returns:
        UserPortfolio: ユーザーポートフォリオ
    """
    try:
        portfolio = await firestore_service.get_user_portfolio(user_id, allow_empty=False, raise_http_exception=True)

        logger.info(f"ポートフォリオ取得成功: user_id={user_id}")
        return {"portfolio": portfolio}
    
    except ConnectionError as e:
        logger.error(f"BigQuery Connection Error in get_user_portfolio: {e}")
        raise HTTPException(status_code=503, detail="Could not connect to the database.")
    
    except Exception as e:
        logger.error(f"ポートフォリオ取得エラー: {e}")
        raise HTTPException(status_code=500, detail="ポートフォリオの取得に失敗しました")

