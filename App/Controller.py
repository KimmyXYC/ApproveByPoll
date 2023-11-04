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
from App.Ostracism import Ostracism
from App.JoinRequest import JoinRequest
from utils.Tool import calculate_md5


class BotRunner(object):
    def __init__(self, config, db):
        self.bot = config.bot
        self.proxy = config.proxy
        self.db = db
        self.request_tasks = {}
        self.ostracism_tasks = {}
        self.bot_id = self.bot.botToken.split(":")[0]

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

        @dp.message_handler(commands=["clean_pin_service_msg"])
        async def handle_command_clean_pin_msg(message: types.Message):
            if message.chat.type in ["group", "supergroup"]:
                await Event.set_clean_pin_service_msg(bot, message, self.db, self.bot_id)
            else:
                await message.reply("Please use this command in the group.")

        @dp.message_handler(commands=["set_vote_time"])
        async def handle_command_set_vote_time(message: types.Message):
            if message.chat.type in ["group", "supergroup"]:
                await Event.set_vote_time(bot, message, self.db)
            else:
                await message.reply("Please use this command in the group.")

        @dp.message_handler(commands=["set_ostracism"])
        async def handle_command_set_ostracism(message: types.Message):
            if message.chat.type in ["group", "supergroup"]:
                await Event.set_ostracism(bot, message, self.db, self.bot_id)
            else:
                await message.reply("Please use this command in the group.")

        @dp.message_handler(commands=["ostracism"])
        async def handle_command_ostracism(message: types.Message):
            if message.chat.type in ["group", "supergroup"]:
                status = self.db.get(str(message.chat.id))
                if status:
                    if not status.get("ostracism", False):
                        await message.reply("The ostracism function is not enabled")
                        return
                else:
                    await message.reply("The ostracism function is not enabled")
                    return
                command_args = message.text.split()
                if len(command_args) == 1:
                    if message.reply_to_message is not None:
                        ostracism_id = calculate_md5(
                            f"{message.chat.id}@{message.from_user.id}"
                            f"@{message.reply_to_message.from_user.id}@Ostracism"
                        )
                        ostracism_task = Ostracism(message.chat.id, message.from_user.id,
                                                   message.reply_to_message.from_user.id, self.bot_id)
                        self.ostracism_tasks[ostracism_id] = ostracism_task
                        await ostracism_task.start_ostracism(bot, message)
                    else:
                        await message.reply("Malformed, please reply to the message sent by the user you want to "
                                            "ostracize or use the /ostracism command followed by the user's ID.")
                elif len(command_args) == 2:
                    ostracism_id = calculate_md5(
                        f"{message.chat.id}@{message.from_user.id}@{int(command_args[1])}@Ostracism")
                    ostracism_task = Ostracism(message.chat.id, message.from_user.id,
                                               command_args[1], self.bot_id)
                    self.ostracism_tasks[ostracism_id] = ostracism_task
                    await ostracism_task.start_ostracism(bot, message)
                else:
                    await message.reply("Malformed, please reply to the message sent by the user you want to "
                                        "ostracize or use the /ostracism command followed by the user's ID.")
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
            join_request_id = calculate_md5(f"{request.chat.id}@{request.from_user.id}@Join")
            request_task = JoinRequest(request.chat.id, request.from_user.id, self.bot_id)
            self.request_tasks[join_request_id] = request_task
            await request_task.handle_join_request(bot, request, _config, self.db)

        @dp.callback_query_handler(lambda c: True)
        async def handle_callback_query(callback_query: types.CallbackQuery):
            requests_type = callback_query.data.split("/")[0]
            if requests_type == "Join":
                action = callback_query.data.split("/")[1]
                join_request_id = callback_query.data.split("/")[2]
                request_task = self.request_tasks.get(join_request_id)
                await request_task.handle_button(bot, callback_query, action)
            elif requests_type == "Ostracism":
                action = callback_query.data.split("/")[1]
                ostracism_id = callback_query.data.split("/")[2]
                ostracism_task = self.ostracism_tasks.get(ostracism_id)
                await ostracism_task.handle_button(bot, callback_query, action, self.db)

        asyncio.run(dp.start_polling())
