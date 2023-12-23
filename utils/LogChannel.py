# -*- coding: utf-8 -*-
# @Time: 2023/12/23 19:24 
# @FileName: LogChannel.py
# @Software: PyCharm
# @GitHub: KimmyXYC
from loguru import logger
from aiogram import types


async def log_c(bot, request: types.ChatJoinRequest, log_type, config, admin=None):
    message = f"""
#{log_type}:
Chat: {request.chat.title}
User: {request.from_user.mention}
User ID: {request.from_user.id}
"""
    if admin is not None:
        message += f"Admin: {admin.mention}"
    try:
        await bot.send_message(config.channel, message)
    except Exception as e:
        logger.error(f"Cannot send message to log channel: {e}")
