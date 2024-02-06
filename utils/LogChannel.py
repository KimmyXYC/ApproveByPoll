# -*- coding: utf-8 -*-
# @Time: 2023/12/23 19:24 
# @FileName: LogChannel.py
# @Software: PyCharm
# @GitHub: KimmyXYC
from loguru import logger
from telebot import types


async def log_c(bot, request: types.ChatJoinRequest, log_type, config, admin_mention=None):
    mention = f'<a href="tg://user?id={request.from_user.id}">{request.from_user.first_name}</a>'
    message = f"""
#{log_type}:
<b>Chat</b>: {request.chat.title}
<b>User</b>: {mention}
<b>User ID</b>: <code>{request.from_user.id}</code>
"""
    if admin_mention is not None:
        message += f"<b>Admin</b>: {admin_mention}"
    try:
        await bot.send_message(config.channel, message, parse_mode="HTML")
    except Exception as e:
        logger.error(f"Cannot send message to log channel: {e}")
