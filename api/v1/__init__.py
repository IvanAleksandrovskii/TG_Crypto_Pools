from fastapi import APIRouter

from .chain_views import router as chain_router
from .coin_views import router as coin_router
from .pool_views import router as pool_router
from .offer_views import router as offer_router
from .clicker import router as clicker_router


router = APIRouter()

router.include_router(chain_router, prefix="/chain", tags=["chain"])
router.include_router(coin_router, prefix="/coin", tags=["coin"])
router.include_router(pool_router, prefix="/pool", tags=["pool"])
router.include_router(offer_router, prefix="/offer", tags=["offer"])
router.include_router(clicker_router, prefix="/clicker", tags=["clicker"])
