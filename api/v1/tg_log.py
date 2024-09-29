from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.exc import IntegrityError

from core import logger
from core.models import db_helper
from core.models import TgUser, TgUserLog
from core.schemas import TgUserCreate, TgUserLogCreate

router = APIRouter()


@router.post("/tg-user")
async def create_tg_user(user: TgUserCreate, db: AsyncSession = Depends(db_helper.session_getter)):
    async with db.begin():
        try:
            # Check if user exists
            result = await db.execute(select(TgUser).filter(TgUser.tg_user == user.tg_user))
            existing_user = result.scalar_one_or_none()

            if existing_user:
                logger.info(f"User {user.tg_user} already exists")
                return existing_user

            # If no user found create a new one
            db_user = TgUser(tg_user=user.tg_user)
            db.add(db_user)
            await db.flush()
            await db.refresh(db_user)
            logger.info(f"Created new user: {user.tg_user}")
            return db_user
        except IntegrityError:
            logger.warning(f"Integrity error when creating user {user.tg_user}")
            raise HTTPException(status_code=400, detail="User already exists")
        except Exception as e:
            logger.error(f"Error creating user {user.tg_user}: {str(e)}")
            raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/tg-user-log")  # TODO: Add check if user exists or create (need to ne with cache not to load the db)
async def create_tg_user_log(log: TgUserLogCreate, db: AsyncSession = Depends(db_helper.session_getter)):
    async with db.begin():
        try:
            # Create a log
            db_log = TgUserLog(
                tg_user=log.tg_user,
                url_log=log.url_log if log.url_log else None,
                context=log.context,
            )
            db.add(db_log)

            await db.flush()
            await db.refresh(db_log)
            logger.info(f"Created log for user {log.tg_user}")
            return db_log

        except IntegrityError:
            logger.warning(f"Integrity error when creating log for user {log.tg_user}")
            raise HTTPException(status_code=400, detail="Error creating log")
        except Exception as e:
            logger.error(f"Error creating log for user {log.tg_user}: {str(e)}")
            raise HTTPException(status_code=500, detail="Internal server error")
