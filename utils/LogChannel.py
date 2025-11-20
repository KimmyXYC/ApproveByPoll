# -*- coding: utf-8 -*-
# @Time: 2023/12/23 19:24 
# @FileName: LogChannel.py
# @Software: PyCharm
# @GitHub: KimmyXYC
from loguru import logger
from telebot import types
from setting.telegrambot import BotSetting


class LogChannel:
    def __init__(self, bot):
        self.bot = bot
        self.message = None
        self.channel_id = BotSetting.log_channel
        self.topic_id = BotSetting.log_channel_topic
        self.message_text = None
        self.message = None

    async def create_log(self, request: types.ChatJoinRequest, log_type):
        mention = f'<a href="tg://user?id={request.from_user.id}">{request.from_user.first_name}'
        if request.from_user.last_name is not None:
            mention += f" {request.from_user.last_name}"
        mention += "</a>"
        self.message_text = (
            f"#ApproveByPoll #{log_type}:\n"
            f"<b>Chat</b>: {request.chat.title}\n"
            f"<b>User</b>: {mention}\n"
            f"<b>User ID</b>: <code>{request.from_user.id}</code>"
        )
        message_text = self.message_text + "\n<b>Status</b>: Pending"
        if self.topic_id:
            try:
                self.message = await self.bot.send_message(self.channel_id, message_text, parse_mode="HTML", message_thread_id=int(self.topic_id))
            except Exception as e:
                logger.error(f"Cannot send message to log channel: {e}")
        else:
            try:
                self.message = await self.bot.send_message(self.channel_id, message_text, parse_mode="HTML")
            except Exception as e:
                logger.error(f"Cannot send message to log channel: {e}")

    async def update_log_admin(self, status, admin_mention):
        self.message_text += (
            f"\n<b>Status</b>: {status}\n"
            f"<b>Admin</b>: {admin_mention}"
        )
        try:
            await self.bot.edit_message_text(self.message_text, self.channel_id, self.message.message_id, parse_mode="HTML")
        except Exception as e:
            logger.error(f"Cannot send message to log channel: {e}")

    async def update_log(self, status, allow_count, deny_count):
        self.message_text += (
            f"\n<b>Status</b>: {status}\n"
            f"<b>Result</b>: Allow : Deny = {allow_count} : {deny_count}"
        )
        try:
            await self.bot.edit_message_text(self.message_text, self.channel_id, self.message.message_id, parse_mode="HTML")
        except Exception as e:
            logger.error(f"Cannot send message to log channel: {e}")
