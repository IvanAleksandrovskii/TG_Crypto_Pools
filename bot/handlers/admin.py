import asyncio

from aiogram import types, Router
from aiogram.enums import ContentType
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State

from bot import UserService, logger
from core import settings


router = Router()


class AdminBroadcastStates(StatesGroup):
    WAITING_FOR_MESSAGE = State()
    WAITING_FOR_CONFIRMATION = State()


@router.message(Command("broadcast"))
async def start_broadcast(message: types.Message, state: FSMContext):
    try:
        if not await UserService.is_superuser(int(message.from_user.id)):
            await message.answer("У вас нет прав для выполнения этой команды.")
            return

        await state.set_state(AdminBroadcastStates.WAITING_FOR_MESSAGE)
        await state.update_data(messages=[])

        await message.answer(
            "Введите сообщение для массовой рассылки. Вы можете отправить следующие типы контента:\n\n"
            "• Текст\n"
            "• Фото\n"
            "• Видео\n"
            "• Аудио\n"
            "• Документ\n"
            "• Анимация (GIF)\n"
            "• Голосовое сообщение\n"
            "• Видеозапись\n"
            "• Стикер\n"
            "• Местоположение\n"
            "• Место (venue)\n"
            "• Контакт\n"
            "Вы можете отправить несколько сообщений разных типов. "
            "Когда закончите, отправьте команду /done для подтверждения рассылки."
        )

    except Exception as e:
        logger.error(f"Error in start_broadcast: {e}")
        await message.answer(settings.bot.admin_error_message)


@router.message(Command("done"))
async def process_done_command(message: types.Message, state: FSMContext):
    try:
        data = await state.get_data()
        messages = data.get('messages', [])

        if not messages:
            await message.answer("Вы не добавили ни одного сообщения для рассылки. Пожалуйста, добавьте хотя бы одно сообщение.")
            return

        await message.answer("Вот предварительный просмотр вашей рассылки:")

        grouped_media = []
        grouped_documents = []

        for msg_data in messages:
            msg = msg_data['message']
            entities = msg_data['entities']

            if msg.content_type in [ContentType.PHOTO, ContentType.VIDEO]:
                media = types.InputMediaPhoto(media=msg.photo[-1].file_id) if msg.content_type == ContentType.PHOTO else types.InputMediaVideo(media=msg.video.file_id)
                media.caption = msg.caption
                media.caption_entities = entities
                grouped_media.append(media)

                if len(grouped_media) == 10:
                    await message.bot.send_media_group(message.chat.id, grouped_media)
                    grouped_media = []

            elif msg.content_type == ContentType.DOCUMENT:
                grouped_documents.append((msg.document.file_id, msg.caption, entities))

                if len(grouped_documents) == 10:
                    for doc in grouped_documents:
                        await message.answer_document(doc[0], caption=doc[1], caption_entities=doc[2])
                    grouped_documents = []

            else:
                # Send any remaining grouped media or documents
                if grouped_media:
                    await message.bot.send_media_group(message.chat.id, grouped_media)
                    grouped_media = []
                if grouped_documents:
                    for doc in grouped_documents:
                        await message.answer_document(doc[0], caption=doc[1], caption_entities=doc[2])
                    grouped_documents = []

                # Send other types of content
                if msg.content_type == ContentType.TEXT:
                    await message.answer(msg.text, entities=entities)
                elif msg.content_type == ContentType.AUDIO:
                    await message.answer_audio(msg.audio.file_id, caption=msg.caption, caption_entities=entities)
                elif msg.content_type == ContentType.ANIMATION:
                    await message.answer_animation(msg.animation.file_id, caption=msg.caption, caption_entities=entities)
                elif msg.content_type == ContentType.VOICE:
                    await message.answer_voice(msg.voice.file_id, caption=msg.caption, caption_entities=entities)
                elif msg.content_type == ContentType.VIDEO_NOTE:
                    await message.answer_video_note(msg.video_note.file_id)
                elif msg.content_type == ContentType.STICKER:
                    await message.answer_sticker(msg.sticker.file_id)
                elif msg.content_type == ContentType.LOCATION:
                    await message.answer_location(msg.location.latitude, msg.location.longitude)
                elif msg.content_type == ContentType.VENUE:
                    await message.answer_venue(msg.venue.location.latitude, msg.venue.location.longitude, msg.venue.title, msg.venue.address)
                elif msg.content_type == ContentType.CONTACT:
                    await message.answer_contact(msg.contact.phone_number, msg.contact.first_name, msg.contact.last_name)
                else:
                    await message.answer(f"Неподдерживаемый тип сообщения: {msg.content_type}")

        # Send any remaining grouped media or documents
        if grouped_media:
            await message.bot.send_media_group(message.chat.id, grouped_media)
        if grouped_documents:
            for doc in grouped_documents:
                await message.answer_document(doc[0], caption=doc[1], caption_entities=doc[2])

        await state.set_state(AdminBroadcastStates.WAITING_FOR_CONFIRMATION)
        await message.answer(
            f"Вы добавили {len(messages)} сообщение(й) для рассылки. Вы уверены, что хотите начать рассылку? (да/нет)")

    except Exception as e:
        logger.error(f"Error in process_done_command: {e}")
        await message.answer(settings.bot.admin_error_message)


@router.message(AdminBroadcastStates.WAITING_FOR_MESSAGE)
async def process_broadcast_message(message: types.Message, state: FSMContext):
    try:
        data = await state.get_data()
        messages = data.get('messages', [])

        messages.append({
            'message': message,
            'entities': message.entities or message.caption_entities
        })

        await state.update_data(messages=messages)
        await message.answer("Сообщение добавлено в рассылку. Отправьте еще сообщения или используйте /done для завершения.")
    except Exception as e:
        logger.error(f"Error in process_broadcast_message: {e}")
        await message.answer(settings.bot.admin_error_message)


@router.message(AdminBroadcastStates.WAITING_FOR_CONFIRMATION)
async def confirm_broadcast(message: types.Message, state: FSMContext):
    user_service = UserService()

    try:
        if message.text.lower() not in settings.bot.confirming_words:
            await message.answer("Рассылка отменена.")
            await state.clear()
            return

        data = await state.get_data()
        broadcast_messages = data['messages']

        all_users = await user_service.get_all_users()
        failed_users = []
        users_counter = 0

        for user in all_users:
            try:
                grouped_media = []
                grouped_documents = []

                for msg_data in broadcast_messages:
                    msg = msg_data['message']
                    entities = msg_data['entities']

                    if msg.content_type in [ContentType.PHOTO, ContentType.VIDEO]:
                        media = types.InputMediaPhoto(media=msg.photo[-1].file_id) if msg.content_type == ContentType.PHOTO else types.InputMediaVideo(media=msg.video.file_id)
                        media.caption = msg.caption
                        media.caption_entities = entities
                        grouped_media.append(media)

                        if len(grouped_media) == 10:
                            await message.bot.send_media_group(int(user.tg_user), grouped_media)
                            grouped_media = []

                    elif msg.content_type == ContentType.DOCUMENT:
                        grouped_documents.append((msg.document.file_id, msg.caption, entities))

                        if len(grouped_documents) == 10:
                            for doc in grouped_documents:
                                await message.bot.send_document(int(user.tg_user), doc[0], caption=doc[1], caption_entities=doc[2])
                            grouped_documents = []

                    else:
                        # Send any remaining grouped media or documents
                        if grouped_media:
                            await message.bot.send_media_group(int(user.tg_user), grouped_media)
                            grouped_media = []
                        if grouped_documents:
                            for doc in grouped_documents:
                                await message.bot.send_document(int(user.tg_user), doc[0], caption=doc[1], caption_entities=doc[2])
                            grouped_documents = []

                        # Send other types of content
                        if msg.content_type == ContentType.TEXT:
                            await message.bot.send_message(int(user.tg_user), msg.text, entities=entities)
                        elif msg.content_type == ContentType.AUDIO:
                            await message.bot.send_audio(int(user.tg_user), msg.audio.file_id, caption=msg.caption, caption_entities=entities)
                        elif msg.content_type == ContentType.ANIMATION:
                            await message.bot.send_animation(int(user.tg_user), msg.animation.file_id, caption=msg.caption, caption_entities=entities)
                        elif msg.content_type == ContentType.VOICE:
                            await message.bot.send_voice(int(user.tg_user), msg.voice.file_id, caption=msg.caption, caption_entities=entities)
                        elif msg.content_type == ContentType.VIDEO_NOTE:
                            await message.bot.send_video_note(int(user.tg_user), msg.video_note.file_id)
                        elif msg.content_type == ContentType.STICKER:
                            await message.bot.send_sticker(int(user.tg_user), msg.sticker.file_id)
                        elif msg.content_type == ContentType.LOCATION:
                            await message.bot.send_location(int(user.tg_user), msg.location.latitude, msg.location.longitude)
                        elif msg.content_type == ContentType.VENUE:
                            await message.bot.send_venue(int(user.tg_user), msg.venue.location.latitude, msg.venue.location.longitude, msg.venue.title, msg.venue.address)
                        elif msg.content_type == ContentType.CONTACT:
                            await message.bot.send_contact(int(user.tg_user), msg.contact.phone_number, msg.contact.first_name, msg.contact.last_name)
                        else:
                            await message.bot.send_message(int(user.tg_user), f"Извините, не поддерживаемый тип контента: {msg.content_type}.")

                # Send any remaining grouped media or documents
                if grouped_media:
                    await message.bot.send_media_group(int(user.tg_user), grouped_media)
                if grouped_documents:
                    for doc in grouped_documents:
                        await message.bot.send_document(int(user.tg_user), doc[0], caption=doc[1], caption_entities=doc[2])

                users_counter += 1

                # Sleep to avoid API-flooding/spam block from Telegram
                await asyncio.sleep(0.05)

            except Exception as e:
                logger.info(f"Failed to send broadcast to user {user.tg_user}: {str(e)}")
                failed_users.append(user.tg_user)
                continue

        if failed_users:
            await message.answer(
                f"Рассылка выполнена, успешно отправлено {users_counter} пользователям, "
                f"но не удалось отправить сообщение {len(failed_users)} пользователям. "
                f"Пользователи могли не активировать чат с ботом.")
        else:
            await message.answer(f"Рассылка выполнена успешно: отправлено всем {users_counter} пользователям.")

        await state.clear()
    except Exception as e:
        logger.error(f"Error in confirm_broadcast: {e}")
        await message.answer(settings.bot.admin_error_message)
