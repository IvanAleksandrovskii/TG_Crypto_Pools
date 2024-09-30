from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.exc import IntegrityError
from async_lru import alru_cache

from core import logger, settings
from core.models import db_helper
from core.models import TgUser, TgUserLog
from core.schemas import TgUserCreate, TgUserLogCreate

router = APIRouter()


@alru_cache(ttl=(60 * 60 * int(settings.tg_log.user_cache_ttl_hours)), maxsize=settings.tg_log.users_cache_max_count)
async def get_or_create_user(user_id: int, db: AsyncSession) -> TgUser:
    result = await db.execute(select(TgUser).filter(TgUser.tg_user == user_id))
    user = result.scalar_one_or_none()

    if not user:
        user = TgUser(tg_user=user_id)
        db.add(user)
        await db.flush()
        await db.refresh(user)
        logger.info(f"Created new user: {user_id}")

    return user


@router.post("/tg-user")
async def create_tg_user(user: TgUserCreate, db: AsyncSession = Depends(db_helper.session_getter)):
    try:
        db_user = await get_or_create_user(user.tg_user, db)
        return db_user
    except IntegrityError:
        logger.warning(f"Integrity error when creating user {user.tg_user}")
        raise HTTPException(status_code=400, detail="User already exists")
    except Exception as e:
        logger.error(f"Error creating user {user.tg_user}: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/tg-user-log")
async def create_tg_user_log(log: TgUserLogCreate, db: AsyncSession = Depends(db_helper.session_getter)):
    try:
        # Check if user exists or create new one (using cache)
        await get_or_create_user(log.tg_user, db)

        # Create a log
        db_log = TgUserLog(
            tg_user=log.tg_user,
            url_log=log.url_log if log.url_log else None,
            context=log.context,
        )
        db.add(db_log)

        await db.commit()
        await db.refresh(db_log)
        logger.info(f"Created log for user {log.tg_user}")
        return db_log

    except IntegrityError:
        await db.rollback()
        logger.warning(f"Integrity error when creating log for user {log.tg_user}")
        raise HTTPException(status_code=400, detail="Error creating log")
    except Exception as e:
        await db.rollback()
        logger.error(f"Error creating log for user {log.tg_user}: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")
