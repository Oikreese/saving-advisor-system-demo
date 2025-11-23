import logging
import sys
from app.core.config import settings

def setup_logging():
    logging.basicConfig(
        level=getattr(logging, settings.LOG_LEVEL),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    # httpxのノイズが多いログを完全に無効化
    logging.getLogger("httpx").setLevel(logging.ERROR)
    logging.getLogger("httpcore").setLevel(logging.ERROR)
    logging.getLogger("httpcore.http11").setLevel(logging.ERROR)
    logging.getLogger("httpcore.connection").setLevel(logging.ERROR)
    logging.getLogger("sse_starlette").setLevel(logging.ERROR)
    logging.getLogger("sse_starlette.sse").setLevel(logging.ERROR)
    logging.getLogger("openai").setLevel(logging.WARNING)
    
    return logging.getLogger(__name__)

logger = setup_logging()