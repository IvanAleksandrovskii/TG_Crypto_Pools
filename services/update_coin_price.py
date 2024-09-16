import asyncio
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


async def get_all_coins(session):
    query = select(Coin).where(Coin.is_active == True)
    result = await session.execute(query)
    coins = result.scalars().all()
    return coins


async def update_coin_prices():
    async for session in db_helper.session_getter():
        try:
            all_active_coins = await get_all_coins(session)

            coins_data = [(coin.id, coin.coin_id_for_price_getter) for coin in all_active_coins
                          if coin.coin_id_for_price_getter is not None]

            crypto_ids = [coin[1] for coin in coins_data]

            prices = await get_crypto_prices(crypto_ids)

            updated_coins = 0
            for _coin_id, coingecko_id in coins_data:
                if coingecko_id in prices and 'usd' in prices[coingecko_id]:
                    _price = prices[coingecko_id]['usd']

                    # Format price for storage and display
                    formatted_price = format_price(_price)

                    # Convert formatted price back to float for storage
                    stored_price = float(formatted_price)

                    # Create new CoinPrice instance with formatted price
                    new_price = CoinPrice(coin_id=_coin_id, price=stored_price)
                    session.add(new_price)

                    updated_coins += 1
                    logger.info(f"Updated price for coin ID {_coin_id}: {formatted_price}")
                else:
                    logger.warning(f"Could not fetch price for coin ID {_coin_id}")

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


if __name__ == "__main__":
    asyncio.run(update_coin_prices())
