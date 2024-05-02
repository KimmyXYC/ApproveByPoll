# -*- coding: utf-8 -*-
# @Time: 2023/6/16 17:50
# @FileName: Event.py
# @Software: PyCharm
# @GitHub: KimmyXYC
from loguru import logger
import gettext
from telebot import types

_ = gettext.gettext


async def start(bot, message: types.Message):
    _url_info = _("Open-source repository:")
    _url = "https://github.com/KimmyXYC/ApproveByPoll"
    _info = _("This is a Bot for voting to join the group.")
    await bot.reply_to(
        message,
        f"{_info}\n\n{_url_info} {_url}",
        disable_web_page_preview=True
    )


async def set_vote_time(bot, message: types.Message, db):
    chat_member = await bot.get_chat_member(message.chat.id, message.from_user.id)
    if (chat_member.status == 'administrator' and chat_member.can_invite_users) \
            or chat_member.status == 'creator' or message.from_user.username == "GroupAnonymousBot":
        if message.from_user.username == "GroupAnonymousBot":
            await bot.reply_to(message, _("As an anonymous administrator, please use the Dashboard for this purpose."))
            return
        command_args = message.text.split()
        if len(command_args) != 2:
            await bot.reply_to(message, _("Malformed, expected /set_vote_time [time]"))
            return
        try:
            time = int(command_args[1])
            if time > 3600 or time < 10:
                await bot.reply_to(message, _("Time should be in range [10, 3600]"))
                return
            await bot.reply_to(message, _("Set vote time to {} seconds").format(time))
            chat_dict = db.get(str(message.chat.id))
            if chat_dict is None:
                chat_dict = {}
            chat_dict["vote_time"] = time
            db.set(str(message.chat.id), chat_dict)
        except ValueError:
            await bot.reply_to(message, _("Malformed, expected /set_vote_time [time]"))
    else:
        await bot.reply_to(message, _("You don't have permission to do this."))
