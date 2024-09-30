from core.admin.models.coin_pool_offer import CoinPoolOfferAdmin
from core.admin.models.pool import PoolAdmin
from core.admin.models.coin import CoinAdmin
from core.admin.models.chain import ChainAdmin
from core.admin.models.coin_price import CoinPriceAdmin
from .clicker import ClickerAdmin
from .tg_log import TgUserLogAdmin, TgUserAdmin
from .tg_welcome_message import WelcomeMessageAdmin


# Register admin views
def setup_admin(admin):
    admin.add_view(ChainAdmin)
    admin.add_view(CoinAdmin)
    admin.add_view(PoolAdmin)
    admin.add_view(CoinPoolOfferAdmin)
    admin.add_view(CoinPriceAdmin)
    admin.add_view(ClickerAdmin)
    admin.add_view(TgUserLogAdmin)
    admin.add_view(TgUserAdmin)
    admin.add_view(WelcomeMessageAdmin)
