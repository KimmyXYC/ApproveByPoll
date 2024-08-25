# -*- coding: utf-8 -*-
# @Time: 2023/6/16 17:46
# @FileName: Controller.py
# @Software: PyCharm
# @GitHub: KimmyXYC
import base64
from asgiref.sync import sync_to_async
from loguru import logger
from telebot import types
from telebot import util
from telebot.async_telebot import AsyncTeleBot
from telebot.asyncio_helper import ApiTelegramException
from telebot.asyncio_storage import StateMemoryStorage

from setting.telegrambot import BotSetting
from app import Event, DashBoard, KickRequest
from app.JoinRequest import JoinRequest

StepCache = StateMemoryStorage()


@sync_to_async
def sync_to_async_func():
    pass


class BotRunner(object):
    def __init__(self, db):
        self.bot = AsyncTeleBot(BotSetting.token, state_storage=StepCache)
        self.db = db
        self.bot_id = BotSetting.bot_id
        self.log_channel = BotSetting.log_channel
        self.kick_tasks = {}  # Dict used to store kick requests
        self.join_tasks = {}  # Dict used to store join requests

    async def run(self):
        logger.info("Bot Start")
        bot = self.bot
        if BotSetting.proxy_address:
            from telebot import asyncio_helper

            asyncio_helper.proxy = BotSetting.proxy_address
            logger.info("Proxy tunnels are being used!")
        await self.bot.set_my_commands([
            types.BotCommand("help", "Show help"),
        ], scope=types.BotCommandScopeAllPrivateChats())
        await self.bot.set_my_commands([
            types.BotCommand("setting", "Open Settings Dashboard"),
            types.BotCommand("set_vote_time", "Setting the polling time (unit: s)"),
            types.BotCommand("start_kick_vote", "Initiate a banishment"),
        ], scope=types.BotCommandScopeAllGroupChats())

        @bot.message_handler(commands=["start"], chat_types=['private'])
        async def handle_command(message: types.Message):
            start_param = message.text.split(' ')[-1]
            if start_param.startswith("getresult_"):
                join_request_id = start_param.split("_")[-1]
                join_request_id = base64.b64decode(join_request_id.encode()).decode()
                if join_request_id in self.join_tasks:
                    poll_result = self.join_tasks[join_request_id].get_poll_result(message)
                    if poll_result is not None:
                        await bot.reply_to(message, poll_result)
                    else:
                        await bot.reply_to(message, "Illegal requests")
                else:
                    await bot.reply_to(message, "Illegal requests")
            else:
                await Event.start(bot, message)

        @bot.message_handler(commands=["help"], chat_types=['private'])
        async def handle_command_help(message: types.Message):
            await Event.start(bot, message)

        @bot.message_handler(commands=["setting"], chat_types=['group', 'supergroup'])
        async def handle_command_setting(message: types.Message):
            await DashBoard.homepage(bot, message, self.db, self.bot_id)

        @bot.message_handler(commands=["set_vote_time"], chat_types=['group', 'supergroup'])
        async def handle_command_set_vote_time(message: types.Message):
            await Event.set_vote_time(bot, message, self.db)

        @bot.message_handler(commands=["start_kick_vote"], chat_types=['group', 'supergroup'])
        async def handle_command_start_kick_vote(message: types.Message):
            chat_dict = self.db.get(str(message.chat.id))
            if chat_dict is None:
                chat_dict = {}
            vote_to_kick = chat_dict.get("vote_to_kick", False)
            if not vote_to_kick:
                await bot.reply_to(message, "Vote to kick is not enabled in this chat.")
                return
            if len(message.text.split()) == 1:
                if message.reply_to_message is None:
                    await bot.reply_to(message, "Malformed, expected /start_kick_vote [user_id] or reply to a user.")
                    return
                target_user_id = message.reply_to_message.from_user.id
            elif len(message.text.split()) == 2:
                target_user_id = int(message.text.split()[1])
            else:
                await bot.reply_to(message, "Malformed, expected /start_kick_vote [user_id] or reply to a user.")
                return
            ostracism_id = f"{message.chat.id}@{target_user_id}"
            if ostracism_id in self.kick_tasks:
                ostracism_task = self.kick_tasks[ostracism_id]
                if not ostracism_task.check_up_status():
                    return
            ostracism_task = KickRequest.Ostracism(message.chat.id, message.from_user.id, target_user_id, self.bot_id)
            self.kick_tasks[ostracism_id] = ostracism_task
            await ostracism_task.start_kick_vote(bot, message)

        @bot.message_handler(content_types=['pinned_message'], chat_types=['group', 'supergroup'])
        async def delete_pinned_message(message: types.Message):
            status = self.db.get(str(message.chat.id))
            if not status:
                return
            if status.get("clean_pinned_message", False):
                try:
                    await bot.delete_message(message.chat.id, message.message_id)
                except Exception as e:
                    logger.error(f"Delete pinned message failed: {e}")

        @bot.chat_join_request_handler()
        async def handle_new_chat_members(request: types.ChatJoinRequest):
            chat_dict = self.db.get(str(request.chat.id))
            if chat_dict is None:
                chat_dict = {}
            vote_to_join = chat_dict.get("vote_to_join", True)
            if not vote_to_join:
                return
            join_request_id = f"{request.chat.id}@{request.from_user.id}"
            if join_request_id in self.join_tasks:
                join_task = self.join_tasks[join_request_id]
                if not join_task.check_up_status():
                    return
            join_task = JoinRequest(request.chat.id, request.from_user.id, self.bot_id, self.log_channel)
            self.join_tasks[join_request_id] = join_task
            await join_task.handle_join_request(bot, request, self.db)
            try:
                del self.join_tasks[join_request_id]
            except KeyError:
                pass

        @bot.callback_query_handler(lambda c: True)
        async def handle_callback_query(callback_query: types.CallbackQuery):
            requests_type = callback_query.data.split()[0]
            if requests_type == "JR":
                action = callback_query.data.split()[1]
                join_request_id = callback_query.data.split()[2]
                if join_request_id in self.join_tasks:
                    join_task = self.join_tasks.get(join_request_id)
                else:
                    return
                await join_task.handle_button(bot, callback_query, action)
                if join_task.check_up_status():
                    try:
                        del self.join_tasks[join_request_id]
                    except KeyError:
                        pass
            elif requests_type == "KR":
                action = callback_query.data.split()[1]
                ostracism_id = callback_query.data.split()[2]
                if ostracism_id not in self.kick_tasks:
                    return
                ostracism_task = self.kick_tasks.get(ostracism_id)
                await ostracism_task.handle_button(bot, callback_query, action, self.db)
            elif requests_type == "PB":
                request_id = callback_query.data.split()[2]
                if request_id in self.join_tasks:
                    await self.join_tasks[request_id].poll_button_handle(bot, callback_query)
            elif requests_type == "Setting":
                await DashBoard.command_handler(bot, callback_query, self.db, self.bot_id)

        try:
            await bot.polling(
                non_stop=True, allowed_updates=util.update_types, skip_pending=True
            )
        except ApiTelegramException as e:
            logger.opt(exception=e).exception("ApiTelegramException")
        except Exception as e:
            logger.exception(e)
