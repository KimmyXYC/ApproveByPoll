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


class BotRunner(object):
    def __init__(self, config):
        self.bot = config.bot
        self.proxy = config.proxy

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

        @dp.chat_join_request_handler()
        async def handle_new_chat_members(request: types.ChatJoinRequest):
            await Event.handle_join_request(bot, request, _config)

        asyncio.run(dp.start_polling())
