# -*- coding: utf-8 -*-
# @Time: 2024/8/24 下午9:22
# @Author: KimmyXYC
# @File: PollButton.py
# @Software: PyCharm

import base64
import telebot.types
from setting.telegrambot import BotSetting


class PollButton:
    def __init__(self, request_id):
        self.request_id = request_id
        self.finished = False
        self.allow_list = {}
        self.deny_list = {}

    def button_create(self):
        requests_id = base64.b64encode(str(self.request_id).encode()).decode()
        keyboard = telebot.types.InlineKeyboardMarkup()
        keyboard.add(telebot.types.InlineKeyboardButton("Yes", callback_data=f"PB Allow {self.request_id}"),
                     telebot.types.InlineKeyboardButton("No", callback_data=f"PB Deny {self.request_id}"))
        keyboard.add(telebot.types.InlineKeyboardButton("Real-time Result",
                                                        url=f"t.me/{BotSetting.bot_username}?start=getresult_{requests_id}"))
        return keyboard

    async def user_poll_handle(self, bot, call):
        if self.finished:
            await bot.answer_callback_query(call.id, "Poll has ended")
            return
        user_id = call.from_user.id

        if call.from_user.username is not None:
            user_mention = f'@{call.from_user.username}'
        else:
            user_mention = f'<a href="tg://user?id={user_id}">{call.from_user.first_name}'
            if call.from_user.last_name is not None:
                user_mention += f" {call.from_user.last_name}</a>"
            else:
                user_mention += "</a>"

        if user_id in self.allow_list:
            await bot.answer_callback_query(call.id, "You have already voted")
        elif user_id in self.deny_list:
            await bot.answer_callback_query(call.id, "You have already voted")
        else:
            if call.data == f"PB Allow {self.request_id}":
                self.allow_list[user_id] = user_mention
                await bot.answer_callback_query(call.id, "You have voted to allow")
            elif call.data == f"PB Deny {self.request_id}":
                self.deny_list[user_id] = user_mention
                await bot.answer_callback_query(call.id, "You have voted to deny")
            else:
                await bot.answer_callback_query(call.id, "Invalid operation")

    def stop_poll(self):
        self.finished = True
        return len(self.allow_list), len(self.deny_list)

    def get_result(self, user_id, anonymous_vote=True):
        if user_id not in self.allow_list and user_id not in self.deny_list:
            return -1, -1
        info = f"Allow : Deny = {len(self.allow_list)} : {len(self.deny_list)}"
        if not anonymous_vote:
            info += "\n\n<b>Allow List:</b>\n"
            for user in self.allow_list.values():
                info += f"- {user}\n"
            info += "\n<b>Deny List:</b>\n"
            for user in self.deny_list.values():
                info += f"- {user}\n"
        return info
