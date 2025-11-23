from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.services.data.factory import get_data_service_factory, DataSourceType

router = APIRouter()

class SwitchRequest(BaseModel):
    source: str

@router.post("/switch-data-source", summary="Switch Data Source")
def switch_data_source(switch_request: SwitchRequest):
    """
    Dynamically switch the data source for the entire application.
    This is a powerful debugging and demonstration tool.
    
    - **source**: Can be "mock" or "mercari".
    """
    try:
        new_source_type = DataSourceType(switch_request.source.lower())
        factory = get_data_service_factory()
        factory.switch_data_source(new_source_type)
        
        new_config = factory.get_service_info()
        return {
            "message": f"Data source switched to {new_source_type.value}",
            "new_config": new_config
        }
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid data source type '{switch_request.source}'. Must be one of {[s.value for s in DataSourceType]}."
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to switch data source: {e}"
        )

@router.get("/data-source-status", summary="Get Data Source Status")
def get_data_source_status():
    """
    Get the current status of the data service factory.
    """
    factory = get_data_service_factory()
    return factory.get_service_info()
