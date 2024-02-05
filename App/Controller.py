# -*- coding: utf-8 -*-
# @Time: 2023/6/16 17:46
# @FileName: Controller.py
# @Software: PyCharm
# @GitHub: KimmyXYC
import asyncio
from loguru import logger
from aiogram import Bot, Dispatcher, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from App import Event
from App.JoinRequest import JoinRequest
from utils.Tool import cal_md5


class BotRunner(object):
    def __init__(self, config, db):
        self.bot = config.bot
        self.proxy = config.proxy
        self.config = config
        self.bot_id = self.bot.botToken.split(":")[0]
        self.db = db
        self.join_tasks = {}  # Dict used to store join requests

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
            await Event.start(bot, message)

        @dp.message_handler(commands=["pin_vote_msg"])
        async def handle_command_pin_msg(message: types.Message):
            if message.chat.type in ["group", "supergroup"]:
                await Event.set_pin_message(bot, message, self.db, self.bot_id)
            else:
                await message.reply("Please use this command in the group.")

        @dp.message_handler(commands=["set_vote_time"])
        async def handle_command_set_vote_time(message: types.Message):
            if message.chat.type in ["group", "supergroup"]:
                await Event.set_vote_time(bot, message, self.db)
            else:
                await message.reply("Please use this command in the group.")

        @dp.message_handler(commands=["clean_pin_service_msg"])
        async def handle_command_clean_pin_msg(message: types.Message):
            if message.chat.type in ["group", "supergroup"]:
                await Event.set_clean_pin_service_msg(bot, message, self.db, self.bot_id)
            else:
                await message.reply("Please use this command in the group.")

        @dp.message_handler(content_types=types.ContentTypes.PINNED_MESSAGE)
        async def delete_pinned_message(message: types.Message):
            status = self.db.get(str(message.chat.id))
            if not status:
                return
            if status.get("clean_service_msg", False):
                try:
                    await message.delete()
                except Exception as e:
                    logger.error(f"Delete pinned message failed: {e}")

        @dp.chat_join_request_handler()
        async def handle_new_chat_members(request: types.ChatJoinRequest):
            join_request_id = cal_md5(f"{request.chat.id}@{request.from_user.id}")
            join_task = JoinRequest(request.chat.id, request.from_user.id, self.bot_id, self.config)
            self.join_tasks[join_request_id] = join_task
            await join_task.handle_join_request(bot, request, self.db)

        @dp.callback_query_handler(lambda c: True)
        async def handle_callback_query(callback_query: types.CallbackQuery):
            action = callback_query.data.split()[0]
            join_request_id = callback_query.data.split()[1]
            join_tasks = self.join_tasks.get(join_request_id)
            await join_tasks.handle_button(bot, callback_query, action)

        asyncio.run(dp.start_polling())
