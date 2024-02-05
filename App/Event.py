# -*- coding: utf-8 -*-
# @Time: 2023/6/16 17:50
# @FileName: Event.py
# @Software: PyCharm
# @GitHub: KimmyXYC
from loguru import logger
from aiogram import types


async def start(bot, message: types.Message):
    _url = "https://github.com/KimmyXYC/ApproveByPoll"
    _info = f"This is a Bot for voting to join the group."
    await message.reply(
        f"{_info}\n\nOpen-source repository: {_url}",
        disable_web_page_preview=True,
    )


async def set_pin_message(bot, message: types.Message, db, bot_id):
    bot_member = await bot.get_chat_member(message.chat.id, bot_id)
    if bot_member.status == 'administrator' and bot_member.can_pin_messages:
        chat_member = await bot.get_chat_member(message.chat.id, message.from_user.id)
        if (chat_member.status == 'administrator' and chat_member.can_pin_messages) \
                or chat_member.status == 'creator':
            command_args = message.text.split()
            if len(command_args) != 2:
                await message.reply("Malformed, expected /pin_vote_msg [On/Off]")
                return
            if command_args[1].lower() == "on":
                await message.reply("Enable poll message pinning")
                chat_dict = db.get(str(message.chat.id))
                if chat_dict is None:
                    chat_dict = {}
                chat_dict["pin_msg"] = True
                db.set(str(message.chat.id), chat_dict)
            elif command_args[1].lower() == "off":
                await message.reply("Disable poll message pinning")
                chat_dict = db.get(str(message.chat.id))
                if chat_dict is None:
                    chat_dict = {}
                chat_dict["pin_msg"] = False
                db.set(str(message.chat.id), chat_dict)
            else:
                await message.reply("Malformed, expected /pin_vote_msg [On/Off]")
        else:
            await message.reply("You don't have permission to do this.")
    else:
        await message.reply("I don't have permission to pin messages.")


async def set_clean_pin_service_msg(bot, message: types.Message, db, bot_id):
    bot_member = await bot.get_chat_member(message.chat.id, bot_id)
    if bot_member.status == 'administrator' and bot_member.can_delete_messages:
        chat_member = await bot.get_chat_member(message.chat.id, message.from_user.id)
        if (chat_member.status == 'administrator' and chat_member.can_delete_messages) \
                or chat_member.status == 'creator':
            command_args = message.text.split()
            if len(command_args) != 2:
                await message.reply("Malformed, expected /clean_pin_service_msg [On/Off]")
                return
            if command_args[1].lower() == "on":
                await message.reply("Enable service message cleaning")
                chat_dict = db.get(str(message.chat.id))
                if chat_dict is None:
                    chat_dict = {}
                chat_dict["clean_service_msg"] = True
                db.set(str(message.chat.id), chat_dict)
            elif command_args[1].lower() == "off":
                await message.reply("Disable service message cleaning")
                chat_dict = db.get(str(message.chat.id))
                if chat_dict is None:
                    chat_dict = {}
                chat_dict["clean_service_msg"] = False
                db.set(str(message.chat.id), chat_dict)
            else:
                await message.reply("Malformed, expected /clean_pin_service_msg [On/Off]")
        else:
            await message.reply("You don't have permission to do this.")


async def set_vote_time(bot, message: types.Message, db):
    chat_member = await bot.get_chat_member(message.chat.id, message.from_user.id)
    if (chat_member.status == 'administrator' and chat_member.can_invite_users) \
            or chat_member.status == 'creator':
        command_args = message.text.split()
        if len(command_args) != 2:
            await message.reply("Malformed, expected /set_vote_time [time]")
            return
        try:
            time = int(command_args[1])
            if time > 3600 or time < 10:
                await message.reply("Time should be in range [10, 3600]")
                return
            await message.reply(f"Set vote time to {time} seconds")
            chat_dict = db.get(str(message.chat.id))
            if chat_dict is None:
                chat_dict = {}
            chat_dict["vote_time"] = time
            db.set(str(message.chat.id), chat_dict)
        except ValueError:
            await message.reply("Malformed, expected /set_vote_time [time]")
    else:
        await message.reply("You don't have permission to do this.")
