# -*- coding: utf-8 -*-
# @Time： 2023/6/16 17:46
# @FileName: Controller.py
# @Software： PyCharm
# @GitHub: KimmyXYC
import asyncio
from App import Event
from loguru import logger
from aiogram import Bot, Dispatcher, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from utils.Tool import calculate_md5


class BotRunner(object):
    def __init__(self, config):
        self.bot = config.bot
        self.proxy = config.proxy
        self.request_tasks = {}

    def run(self):
        logger.success("Bot Start")
        storage = MemoryStorage()
        if self.proxy.status:
            bot = Bot(token=self.bot.botToken, proxy=self.proxy.url)
            logger.success("Proxy Set")
        else:
            bot = Bot(token=self.bot.botToken)
        _config = self.bot
        dp = Dispatcher(bot, storage=storage)

        @dp.message_handler(commands=["start", "help"], chat_type=types.ChatType.PRIVATE)
        async def handle_command(message: types.Message):
            await Event.start(bot, message, _config)

        @dp.message_handler(content_types=types.ContentTypes.PINNED_MESSAGE)
        async def delete_pinned_message(message: types.Message):
            await Event.delete_pinned_message(bot, message)

        @dp.chat_join_request_handler()
        async def handle_new_chat_members(request: types.ChatJoinRequest):
            join_request_id = calculate_md5(f"{request.chat.id}@{request.from_user.id}")
            request_task = Event.JoinRequest()
            self.request_tasks[join_request_id] = request_task
            await request_task.handle_join_request(bot, request, _config)

        @dp.callback_query_handler(lambda c: True)
        async def handle_callback_query(callback_query: types.CallbackQuery):
            action = callback_query.data.split("/")[0]
            join_request_id = callback_query.data.split("/")[1]

            request_task = self.request_tasks.get(join_request_id)
            if action == "approve":
                await request_task.handle_button(bot, callback_query, "approve")
            elif action == "reject":
                await request_task.handle_button(bot, callback_query, "reject")
            elif action == "ban":
                await request_task.handle_button(bot, callback_query, "ban")
            else:
                logger.error(f"Unknown action: {action}")

        asyncio.run(dp.start_polling())
