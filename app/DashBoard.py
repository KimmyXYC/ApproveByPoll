# -*- coding: utf-8 -*-
# @Time: 2024/2/8 9:53 
# @FileName: DashBoard.py
# @Software: PyCharm
# @GitHub: KimmyXYC
from telebot import types
from loguru import logger

FORMAT = {
    True: "✅",
    False: "❌"
}
ADDITION = "If you want to change the settings, please click the button below."


def db_analyzer(db, chat_id, data_type="all", default_value=None):
    chat_dict = db.get(str(chat_id))
    if chat_dict is None:
        chat_dict = {}
    if data_type == "all":
        return chat_dict
    else:
        return chat_dict.get(data_type, default_value), chat_dict


def message_creator(chat_id, db, addition=ADDITION):
    chat_dict = db_analyzer(db, chat_id)
    vote_to_join = chat_dict.get("vote_to_join", True)
    vote_to_kick = chat_dict.get("vote_to_kick", False)
    pin_msg = chat_dict.get("pin_msg", False)
    vote_time = chat_dict.get("vote_time", 600)
    clean_pinned_message = chat_dict.get("clean_pinned_message", False)
    anonymous_vote = chat_dict.get("anonymous_vote", True)
    advanced_vote = chat_dict.get("advanced_vote", False)
    # Time format
    minutes = vote_time // 60
    seconds = vote_time % 60
    time_parts = []
    if minutes > 0:
        time_parts.append(f"{minutes} minute{'s' if minutes > 1 else ''}")
    if seconds > 0:
        time_parts.append(f"{seconds} second{'s' if seconds > 1 else ''}")
    _time = " and ".join(time_parts) if time_parts else "0 seconds"

    reply_message = (
            f"<b>Group Setting</b>\n\n"
            f"<b>Vote To Join</b>: {vote_to_join}\n"
            f"<b>Vote To Kick</b>: {vote_to_kick}\n"
            f"<b>Vote Time</b>: {_time}\n"
            f"<b>Pin Vote Message</b>: {pin_msg}\n"
            f"<b>Clean Pinned Message</b>: {clean_pinned_message}\n"
            f"<b>Anonymous Vote</b>: {anonymous_vote}\n"
            f"<b>Advanced Vote</b>: {advanced_vote}"
    )
    reply_message += f"\n{addition}" if addition else ""

    buttons = button_creator(vote_to_join, vote_to_kick, pin_msg, clean_pinned_message, chat_id, anonymous_vote, advanced_vote)

    return reply_message, buttons


def button_creator(vote_to_join, vote_to_kick, pin_msg, clean_pinned_message, chat_id, anonymous_vote, advanced_vote):
    buttons = types.InlineKeyboardMarkup()
    buttons.add(types.InlineKeyboardButton(f"{FORMAT.get(vote_to_join)} Vote To Join",
                                           callback_data=f"Setting vote_to_join {chat_id}"),
                types.InlineKeyboardButton(f"{FORMAT.get(vote_to_kick)} Vote To Kick",
                                           callback_data=f"Setting vote_to_kick {chat_id}"))
    buttons.add(types.InlineKeyboardButton("Set Vote Time",
                                           callback_data=f"Setting vote_time {chat_id}"))
    buttons.add(types.InlineKeyboardButton(f"{FORMAT.get(pin_msg)} Pin Vote Message",
                                           callback_data=f"Setting pin_msg {chat_id}"),
                types.InlineKeyboardButton(f"{FORMAT.get(clean_pinned_message)} Clean Pinned Message",
                                           callback_data=f"Setting clean_pinned_message {chat_id}"))
    buttons.add(types.InlineKeyboardButton(f"{FORMAT.get(anonymous_vote)} Anonymous Vote",
                                           callback_data=f"Setting anonymous_vote {chat_id}"),
                types.InlineKeyboardButton(f"{FORMAT.get(advanced_vote)} Advanced Vote",
                                           callback_data=f"Setting advanced_vote {chat_id}"))
    buttons.add(types.InlineKeyboardButton("Close", callback_data="Setting close"))
    return buttons


async def homepage(bot, message: types.Message, db, bot_id):
    chat_member = await bot.get_chat_member(message.chat.id, message.from_user.id)
    if (chat_member.status == 'administrator' or
            chat_member.status == 'creator' or message.from_user.username == "GroupAnonymousBot"):
        reply_message, buttons = message_creator(message.chat.id, db)
        await bot.reply_to(
            message,
            reply_message,
            parse_mode="HTML",
            reply_markup=buttons,
            disable_web_page_preview=True
        )
    else:
        await bot.reply_to(message, "You don't have permission to do this.")
    bot_member = await bot.get_chat_member(message.chat.id, bot_id)
    if bot_member.status == 'administrator' and bot_member.can_delete_messages:
        await bot.delete_message(message.chat.id, message.message_id)


async def homepage_back(bot, callback_query, db, chat_member):
    if chat_member.status == 'administrator' or chat_member.status == 'creator':
        reply_message, buttons = message_creator(callback_query.message.chat.id, db)
        await bot.edit_message_text(
            reply_message,
            callback_query.message.chat.id,
            callback_query.message.message_id,
            parse_mode="HTML",
            reply_markup=buttons,
            disable_web_page_preview=True
        )
    else:
        await bot.answer_callback_query(callback_query.id, "You don't have permission to do this.")
        return


async def command_handler(bot, callback_query: types.CallbackQuery, db, bot_id):
    requests_type = callback_query.data.split()[1]
    chat_member = await bot.get_chat_member(callback_query.message.chat.id, callback_query.from_user.id)
    bot_member = await bot.get_chat_member(callback_query.message.chat.id, bot_id)
    if chat_member.status != 'administrator' and chat_member.status != 'creator':
        await bot.answer_callback_query(callback_query.id, "You don't have permission to do this.")
        return
    if requests_type == "vote_to_join":
        await vote_to_join_handler(bot, callback_query, db, chat_member)
    elif requests_type == "vote_to_kick":
        await vote_to_kick_handler(bot, callback_query, db, chat_member)
    elif requests_type == "vote_time":
        await vote_time_handler(bot, callback_query, db, chat_member)
    elif requests_type == "edit_vote_time":
        await edit_vote_time_handler(bot, callback_query, db, chat_member)
    elif requests_type == "pin_msg":
        await pin_msg_handler(bot, callback_query, db, chat_member, bot_member)
    elif requests_type == "clean_pinned_message":
        await clean_pinned_message_handler(bot, callback_query, db, chat_member, bot_member)
    elif requests_type == "anonymous_vote":
        await anonymous_vote_handler(bot, callback_query, db, chat_member)
    elif requests_type == "advanced_vote":
        await advanced_vote_handler(bot, callback_query, db, chat_member)
    elif requests_type == "back":
        await homepage_back(bot, callback_query, db, chat_member)
    elif requests_type == "close":
        chat_member = await bot.get_chat_member(callback_query.message.chat.id, callback_query.from_user.id)
        if chat_member.status == 'creator' or chat_member.status == 'administrator':
            await bot.delete_message(callback_query.message.chat.id, callback_query.message.message_id)
    else:
        await bot.answer_callback_query(callback_query.id, "Unknown request.")
        logger.error(f"Unknown request: {callback_query.data}")


async def vote_to_join_handler(bot, callback_query: types.CallbackQuery, db, chat_member):
    if chat_member.status != 'creator' and (chat_member.status != 'administrator' or not chat_member.can_invite_users):
        await bot.answer_callback_query(callback_query.id, "You don't have permission to do this.")
        return
    chat_id = int(callback_query.data.split()[2])
    vote_to_join, chat_dict = db_analyzer(db, chat_id, "vote_to_join", True)
    if vote_to_join:
        chat_dict["vote_to_join"] = False
        db.set(str(chat_id), chat_dict)
    else:
        chat_dict["vote_to_join"] = True
        db.set(str(chat_id), chat_dict)
    reply_message, buttons = message_creator(chat_id, db)
    await bot.edit_message_text(
        reply_message,
        callback_query.message.chat.id,
        callback_query.message.message_id,
        parse_mode="HTML",
        reply_markup=buttons,
        disable_web_page_preview=True
    )


async def vote_to_kick_handler(bot,  callback_query: types.CallbackQuery, db, chat_member):
    if chat_member.status != 'creator' and (
            chat_member.status != 'administrator' or not chat_member.can_restrict_members):
        await bot.answer_callback_query(callback_query.id, "You don't have permission to do this.")
        return
    chat_id = int(callback_query.data.split()[2])
    vote_to_kick, chat_dict = db_analyzer(db, chat_id, "vote_to_kick", False)
    if vote_to_kick:
        chat_dict["vote_to_kick"] = False
        db.set(str(chat_id), chat_dict)
    else:
        chat_dict["vote_to_kick"] = True
        db.set(str(chat_id), chat_dict)
    reply_message, buttons = message_creator(chat_id, db)
    await bot.edit_message_text(
        reply_message,
        callback_query.message.chat.id,
        callback_query.message.message_id,
        parse_mode="HTML",
        reply_markup=buttons,
        disable_web_page_preview=True
    )


async def vote_time_handler(bot, callback_query: types.CallbackQuery, db, chat_member):
    if chat_member.status != 'creator' and (chat_member.status != 'administrator' or not chat_member.can_change_info):
        await bot.answer_callback_query(callback_query.id, "You don't have permission to do this.")
        return
    chat_id = int(callback_query.data.split()[2])
    addition = "If you want to change the vote time precisely, please use the command /set_vote_time"
    reply_message, _ = message_creator(chat_id, db, addition)
    buttons = types.InlineKeyboardMarkup()
    buttons.add(types.InlineKeyboardButton("1 min", callback_data=f"Setting edit_vote_time {chat_id} 60"),
                types.InlineKeyboardButton("2 min", callback_data=f"Setting edit_vote_time {chat_id} 120"),
                types.InlineKeyboardButton("3 min", callback_data=f"Setting edit_vote_time {chat_id} 180"))
    buttons.add(types.InlineKeyboardButton("5min", callback_data=f"Setting edit_vote_time {chat_id} 300"),
                types.InlineKeyboardButton("10min", callback_data=f"Setting edit_vote_time {chat_id} 600"),
                types.InlineKeyboardButton("15min", callback_data=f"Setting edit_vote_time {chat_id} 900"))
    buttons.add(types.InlineKeyboardButton("20min", callback_data=f"Setting edit_vote_time {chat_id} 1200"),
                types.InlineKeyboardButton("30min", callback_data=f"Setting edit_vote_time {chat_id} 1800"),
                types.InlineKeyboardButton("60min", callback_data=f"Setting edit_vote_time {chat_id} 3600"))
    buttons.add(types.InlineKeyboardButton("⬅️ Go Back", callback_data="Setting back"))
    await bot.edit_message_text(
        reply_message,
        callback_query.message.chat.id,
        callback_query.message.message_id,
        parse_mode="HTML",
        reply_markup=buttons,
        disable_web_page_preview=True
    )


async def edit_vote_time_handler(bot, callback_query: types.CallbackQuery, db, chat_member):
    if chat_member.status != 'creator' and (chat_member.status != 'administrator' or not chat_member.can_change_info):
        await bot.answer_callback_query(callback_query.id, "You don't have permission to do this.")
        return
    chat_id = int(callback_query.data.split()[2])
    vote_time = int(callback_query.data.split()[3])
    chat_dict = db_analyzer(db, chat_id, "all")
    chat_dict["vote_time"] = vote_time
    db.set(str(chat_id), chat_dict)
    reply_message, buttons = message_creator(chat_id, db)
    await bot.edit_message_text(
        reply_message,
        callback_query.message.chat.id,
        callback_query.message.message_id,
        parse_mode="HTML",
        reply_markup=buttons,
        disable_web_page_preview=True
    )


async def pin_msg_handler(bot, callback_query: types.CallbackQuery, db, chat_member, bot_member):
    if bot_member.status != 'administrator' or not bot_member.can_pin_messages:
        await bot.answer_callback_query(callback_query.id, "I don't have permission to pin messages.")
        return
    if chat_member.status != 'creator' and (chat_member.status != 'administrator' or not chat_member.can_pin_messages):
        await bot.answer_callback_query(callback_query.id, "You don't have permission to do this.")
        return
    chat_id = int(callback_query.data.split()[2])
    pin_msg, chat_dict = db_analyzer(db, chat_id, "pin_msg", False)
    if pin_msg:
        chat_dict["pin_msg"] = False
        db.set(str(chat_id), chat_dict)
    else:
        chat_dict["pin_msg"] = True
        db.set(str(chat_id), chat_dict)
    reply_message, buttons = message_creator(chat_id, db)
    await bot.edit_message_text(
        reply_message,
        callback_query.message.chat.id,
        callback_query.message.message_id,
        parse_mode="HTML",
        reply_markup=buttons,
        disable_web_page_preview=True
    )


async def clean_pinned_message_handler(bot, callback_query: types.CallbackQuery, db, chat_member, bot_member):
    if bot_member.status != 'administrator' or not bot_member.can_delete_messages:
        await bot.answer_callback_query(callback_query.id, "I don't have permission to delete messages.")
        return
    if chat_member.status != 'creator' and (
            chat_member.status != 'administrator' or not chat_member.can_delete_messages):
        await bot.answer_callback_query(callback_query.id, "You don't have permission to do this.")
        return
    chat_id = int(callback_query.data.split()[2])
    clean_pinned_message, chat_dict = db_analyzer(db, chat_id, "clean_pinned_message", False)
    if clean_pinned_message:
        chat_dict["clean_pinned_message"] = False
        db.set(str(chat_id), chat_dict)
    else:
        chat_dict["clean_pinned_message"] = True
        db.set(str(chat_id), chat_dict)
    reply_message, buttons = message_creator(chat_id, db)
    await bot.edit_message_text(
        reply_message,
        callback_query.message.chat.id,
        callback_query.message.message_id,
        parse_mode="HTML",
        reply_markup=buttons,
        disable_web_page_preview=True
    )


async def anonymous_vote_handler(bot, callback_query: types.CallbackQuery, db, chat_member):
    if chat_member.status != 'creator' and (chat_member.status != 'administrator' or not chat_member.can_change_info):
        await bot.answer_callback_query(callback_query.id, "You don't have permission to do this.")
        return
    chat_id = int(callback_query.data.split()[2])
    anonymous_vote, chat_dict = db_analyzer(db, chat_id, "anonymous_vote", True)
    if anonymous_vote:
        chat_dict["anonymous_vote"] = False
        db.set(str(chat_id), chat_dict)
    else:
        chat_dict["anonymous_vote"] = True
        db.set(str(chat_id), chat_dict)
    reply_message, buttons = message_creator(chat_id, db)
    await bot.edit_message_text(
        reply_message,
        callback_query.message.chat.id,
        callback_query.message.message_id,
        parse_mode="HTML",
        reply_markup=buttons,
        disable_web_page_preview=True
    )


async def advanced_vote_handler(bot, callback_query: types.CallbackQuery, db, chat_member):
    if chat_member.status != 'creator' and (chat_member.status != 'administrator' or not chat_member.can_change_info):
        await bot.answer_callback_query(callback_query.id, "You don't have permission to do this.")
        return
    chat_id = int(callback_query.data.split()[2])
    advanced_vote, chat_dict = db_analyzer(db, chat_id, "advanced_vote", False)
    if advanced_vote:
        chat_dict["advanced_vote"] = False
        db.set(str(chat_id), chat_dict)
    else:
        chat_dict["advanced_vote"] = True
        db.set(str(chat_id), chat_dict)
    reply_message, buttons = message_creator(chat_id, db)
    await bot.edit_message_text(
        reply_message,
        callback_query.message.chat.id,
        callback_query.message.message_id,
        parse_mode="HTML",
        reply_markup=buttons,
        disable_web_page_preview=True
    )
