import aiohttp
import sys
import os

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)

from core import logger
from core.models import db_helper
from core.models.coin import Coin
from core.models.coin_price import CoinPrice


coins_should_exist = {
    "LAVA": "lava-network",
    "CRO": "crypto-com-chain",
    "TIA": "celestia",
    "LUNC": "terra-luna",
    "SAGA": "saga-2",
    "COREUM": "coreum",
    "POL": "matic-network",
    "DYDX": "dydx",
    "DYM": "dymension",
    "ISLM": "islamic-coin",
    "NLS": "nolus",
    "ETH": "ethereum",
}


async def check_coins_exist_or_create(session, coins_from_db):
    coins_from_db_codes = [coin.code for coin in coins_from_db]
    coins_to_create = []
    for coin, coin_price_getting_id in coins_should_exist.items():
        if coin not in coins_from_db_codes:
            new_coin = Coin(code=coin, coin_id_for_price_getter=coin_price_getting_id, is_active=True)
            coins_to_create.append(new_coin)
    if coins_to_create:
        session.add_all(coins_to_create)
        await session.commit()
        query = select(Coin).where(Coin.is_active == True)
        result = await session.execute(query)
        coins = result.scalars().all()
        return coins
    return [coin for coin in coins_from_db if coin.is_active]


async def get_all_coins(session):
    query = select(Coin)
    result = await session.execute(query)
    coins_from_db = result.scalars().all()
    coins = await check_coins_exist_or_create(session, coins_from_db)
    return coins


def format_price(_price):
    if _price < 0.00000001:
        return f"{_price:.8e}"
    elif _price < 0.00001:
        return f"{_price:.8f}"
    elif _price < 0.0001:
        return f"{_price:.7f}"
    elif _price < 0.001:
        return f"{_price:.6f}"
    elif _price < 0.01:
        return f"{_price:.5f}"
    elif _price < 0.1:
        return f"{_price:.4f}"
    elif _price < 1:
        return f"{_price:.3f}"
    elif _price < 10:
        return f"{_price:.2f}"
    else:
        return f"{_price:.2f}"


async def get_crypto_prices(crypto_ids):
    url = f"https://api.coingecko.com/api/v3/simple/price?ids={','.join(crypto_ids)}&vs_currencies=usd"
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            return await response.json()


async def update_coin_prices():
    async for session in db_helper.session_getter():
        try:
            all_active_coins = await get_all_coins(session)

            crypto_ids = [coin.coin_id_for_price_getter for coin in all_active_coins
                          if coin.coin_id_for_price_getter is not None]

            prices = await get_crypto_prices(crypto_ids)

            updated_coins = 0
            for coin in all_active_coins:
                if coin.coin_id_for_price_getter in prices and 'usd' in prices[coin.coin_id_for_price_getter]:
                    _price = prices[coin.coin_id_for_price_getter]['usd']

                    # Format price for storage and display
                    formatted_price = format_price(_price)

                    # Convert formatted price back to float for storage
                    stored_price = float(formatted_price)

                    # Create new CoinPrice instance with formatted price
                    new_price = CoinPrice(coin_id=coin.id, price=stored_price)
                    session.add(new_price)

                    updated_coins += 1
                    logger.info(f"Updated price for coin {coin.code}: {formatted_price}")
                else:
                    logger.warning(f"Could not fetch price for coin {coin.code}")

            await session.commit()
            logger.info(f"Successfully updated prices for {updated_coins} coins")

        except SQLAlchemyError as e:
            await session.rollback()
            logger.error(f"Database error occurred: {str(e)}")
        except aiohttp.ClientError as e:
            logger.error(f"API request error occurred: {str(e)}")
        except Exception as e:
            await session.rollback()
            logger.error(f"An unexpected error occurred: {str(e)}")

        finally:
            await session.close()


# if __name__ == "__main__":
#     import asyncio
#     asyncio.run(update_coin_prices())
