from core.admin.models.coin_pool_offer import CoinPoolOfferAdmin
from core.admin.models.pool import PoolAdmin
from core.admin.models.coin import CoinAdmin
from core.admin.models.chain import ChainAdmin


# Register admin views
def setup_admin(admin):
    admin.add_view(ChainAdmin)
    admin.add_view(CoinAdmin)
    admin.add_view(PoolAdmin)
    admin.add_view(CoinPoolOfferAdmin)
