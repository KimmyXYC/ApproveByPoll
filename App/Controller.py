# -*- coding: utf-8 -*-
# @Time: 2023/6/16 17:46
# @FileName: Controller.py
# @Software: PyCharm
# @GitHub: KimmyXYC
import asyncio
from loguru import logger
from telebot import util, types
from telebot.async_telebot import AsyncTeleBot
from telebot.asyncio_storage import StateMemoryStorage
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

    def botcreate(self):
        bot = AsyncTeleBot(self.bot.botToken, state_storage=StateMemoryStorage())
        return bot, self.bot

    def run(self):
        # print(self.bot)
        logger.success("Bot Start")
        bot, _config = self.botcreate()
        if self.proxy.status:
            from telebot import asyncio_helper
            asyncio_helper.proxy = self.proxy.url
            logger.success("Proxy Set")

        @bot.message_handler(commands=["start", "help"], chat_types=['private'])
        async def handle_command(message: types.Message):
            await Event.start(bot, message)

        @bot.message_handler(commands=["pin_vote_msg"])
        async def handle_command_pin_msg(message: types.Message):
            if message.chat.type in ["group", "supergroup"]:
                await Event.set_pin_message(bot, message, self.db, self.bot_id)
            else:
                await bot.reply_to(message, "Please use this command in the group.")

        @bot.message_handler(commands=["set_vote_time"])
        async def handle_command_set_vote_time(message: types.Message):
            if message.chat.type in ["group", "supergroup"]:
                await Event.set_vote_time(bot, message, self.db)
            else:
                await bot.reply_to(message, "Please use this command in the group.")

        @bot.message_handler(commands=["clean_pin_msg"])
        async def handle_command_clean_pin_msg(message: types.Message):
            if message.chat.type in ["group", "supergroup"]:
                await Event.set_clean_pin_msg(bot, message, self.db, self.bot_id)
            else:
                await bot.reply_to(message, "Please use this command in the group.")

        @bot.message_handler(content_types=['pinned_message'])
        async def delete_pinned_message(message: types.Message):
            status = self.db.get(str(message.chat.id))
            if not status:
                return
            if status.get("clean_service_msg", False):
                try:
                    await bot.delete_message(message.chat.id, message.message_id)
                except Exception as e:
                    logger.error(f"Delete pinned message failed: {e}")

        @bot.chat_join_request_handler()
        async def handle_new_chat_members(request: types.ChatJoinRequest):
            join_request_id = cal_md5(f"{request.chat.id}@{request.from_user.id}")
            if join_request_id in self.join_tasks:
                join_task = self.join_tasks[join_request_id]
                if not join_task.check_up_status():
                    return
            join_task = JoinRequest(request.chat.id, request.from_user.id, self.bot_id, self.config)
            self.join_tasks[join_request_id] = join_task
            await join_task.handle_join_request(bot, request, self.db)
            try:
                del self.join_tasks[join_request_id]
            except KeyError:
                pass

        @bot.callback_query_handler(lambda c: True)
        async def handle_callback_query(callback_query: types.CallbackQuery):
            action = callback_query.data.split()[0]
            join_request_id = callback_query.data.split()[1]
            join_tasks = self.join_tasks.get(join_request_id, None)
            if join_tasks is None:
                return
            await join_tasks.handle_button(bot, callback_query, action)
            if join_tasks.check_up_status():
                try:
                    del self.join_tasks[join_request_id]
                except KeyError:
                    pass

        async def main():
            await asyncio.gather(bot.polling(non_stop=True, allowed_updates=util.update_types))

        asyncio.run(main())
