# -*- coding: utf-8 -*-
# @Time： 2023/6/16 17:50 
# @FileName: Event.py
# @Software： PyCharm
# @GitHub: KimmyXYC
import asyncio
from loguru import logger
from aiogram import types
from utils.Tool import calculate_md5


async def start(bot, message: types.Message):
    _url = "https://github.com/KimmyXYC/ApproveByPoll"
    _info = f"This is a Bot for voting to join the group."
    await message.reply(
        f"{_info}\n\nOpen-source repository: {_url}",
        disable_web_page_preview=True,
    )


async def set_pin_message(bot, message: types.Message, db):
    bot_user = await bot.get_me()
    bot_member = await bot.get_chat_member(message.chat.id, bot_user.id)
    if bot_member.status == 'administrator' and bot_member.can_pin_messages:
        chat_member = await bot.get_chat_member(message.chat.id, message.from_user.id)
        if (chat_member.status == 'administrator' and chat_member.can_pin_messages) or chat_member.status == 'creator':
            command_args = message.text.split()
            if len(command_args) == 1:
                await message.reply("Malformed, expected /pin_vote_msg [On/Off]")
            elif len(command_args) == 2:
                if command_args[1] == "On" or command_args[1] == "on":
                    await message.reply("Enable poll message pinning")
                    db.set(str(message.chat.id), {"pin_msg": True})
                elif command_args[1] == "Off" or command_args[1] == "off":
                    await message.reply("Disable poll message pinning")
                    db.set(str(message.chat.id), {"pin_msg": False})
                else:
                    await message.reply("Malformed, expected /pin_vote_msg [On/Off]")
            else:
                await message.reply("Malformed, expected /pin_vote_msg [On/Off]")


async def delete_pinned_message(bot, message: types.Message, db):
    status = db.get(str(message.chat.id))
    if status:
        if status["pin_msg"]:
            try:
                await message.delete()
            except Exception as e:
                logger.error(f"Delete pinned message failed: {e}")


class JoinRequest:
    def __init__(self, chat_id, user_id):
        self.chat_id = chat_id
        self.user_id = user_id
        self.finished = False

        self.bot_member = None

        self.request = None
        self.user_message = None
        self.notice_message = None
        self.polling = None

    async def handle_join_request(self, bot, request: types.ChatJoinRequest, config, db):
        self.request = request

        bot_user = await bot.get_me()
        self.bot_member = await bot.get_chat_member(self.chat_id, bot_user.id)
        logger.info(f"New join request from {request.from_user.mention}(ID: {self.user_id}) in {self.chat_id}")

        _zh_info = f"您正在申请加入「{request.chat.title}」，结果将于5分钟后告知您。"
        _en_info = f"You are applying to join 「{request.chat.title}」. " \
                   f"The result will be communicated to you in 5 minutes."
        _info = f"由于 Telegram 的限制，首次使用请按下 /start 以便机器人发送申请结果。\n" \
                f"Due to limitations imposed by Telegram, " \
                f"please press /start for the first time to allow the bot to send the application result."
        self.user_message = await bot.send_message(
            self.user_id,
            f"{_zh_info}\n{_en_info}\n\n{_info}",
        )

        join_request_id = calculate_md5(f"{self.chat_id}@{self.user_id}")
        keyboard = types.InlineKeyboardMarkup(row_width=3)
        approve_button = types.InlineKeyboardButton(text="Approve", callback_data=f"Approve/{join_request_id}")
        reject_button = types.InlineKeyboardButton(text="Reject", callback_data=f"Reject/{join_request_id}")
        ban_button = types.InlineKeyboardButton(text="Ban", callback_data=f"Ban/{join_request_id}")
        keyboard.add(approve_button, reject_button, ban_button)

        notice_message = await bot.send_message(
            self.chat_id,
            f"{request.from_user.mention}(ID: {self.user_id}) is requesting to join this group."
            f"\n\n tg://user?id={self.user_id}",
            reply_markup=keyboard
        )
        self.notice_message = notice_message

        vote_question = "Approve this user?"
        vote_options = ["Yes", "No"]
        self.polling = await bot.send_poll(
            self.chat_id,
            vote_question,
            vote_options,
            is_anonymous=True,
            allows_multiple_answers=False,
            reply_to_message_id=notice_message.message_id,
        )
        status = db.get(str(self.chat_id))
        if status:
            status_pin_msg = status["pin_msg"]
        else:
            status_pin_msg = False

        if status_pin_msg and self.bot_member.status == 'administrator' and self.bot_member.can_pin_messages:
            await bot.pin_chat_message(
                chat_id=self.chat_id,
                message_id=self.polling.message_id,
                disable_notification=True,
            )

        await asyncio.sleep(300)

        if self.finished:
            return
        if status_pin_msg and self.bot_member.status == 'administrator' and self.bot_member.can_pin_messages:
            await bot.unpin_chat_message(
                chat_id=self.chat_id,
                message_id=self.polling.message_id,
            )

        vote_message = await bot.stop_poll(request.chat.id, self.polling.message_id)

        allow_count = vote_message.options[0].voter_count
        deny_count = vote_message.options[1].voter_count

        if vote_message.total_voter_count == 0:
            logger.info(f"{self.user_id}: No one voted in {self.chat_id}")
            result_message = await notice_message.reply("No one voted.")
            approve_user = False
            edit_msg = f"{request.from_user.mention}(ID: {self.user_id}): No one voted."
            user_reply_msg = "无人投票，请稍后尝试重新申请。\nNo one voted. Please request again later."
        elif allow_count > deny_count:
            logger.info(f"{self.user_id}: Approved {self.user_id} in {self.chat_id}")
            result_message = await notice_message.reply("通过。\nApproved.")
            approve_user = True
            edit_msg = f"{request.from_user.mention}(ID: {self.user_id}): Approved."
            user_reply_msg = "您已获批准加入\nYou have been approved."
        elif allow_count == deny_count:
            logger.info(f"{self.user_id}: Tie in {self.chat_id}")
            result_message = await notice_message.reply("平票。\nTie.")
            approve_user = False
            edit_msg = f"{request.from_user.mention}(ID: {self.user_id}): Tie."
            user_reply_msg = "平票，请稍后尝试重新申请。\nTie. Please request again later."
        else:
            logger.info(f"{self.user_id}: Denied {self.user_id} in {self.chat_id}")
            result_message = await notice_message.reply("拒绝。\nDenied.")
            approve_user = False
            edit_msg = f"{request.from_user.mention}(ID: {self.user_id}): Denied."
            user_reply_msg = "您的申请已被拒绝。\nYou have been denied."

        try:
            if approve_user:
                await request.approve()
            else:
                await request.decline()
            await notice_message.edit_text(edit_msg)
        except Exception as e:
            logger.error(f"User_id:{self.user_id} in Chat_id:{self.chat_id}: {e}")
        try:
            await self.user_message.reply(user_reply_msg)
        except Exception as e:
            logger.error(f"Send message to User_id:{self.user_id}: {e}")

        await asyncio.sleep(60)

        try:
            await bot.delete_message(chat_id=request.chat.id, message_id=self.polling.message_id)
            await bot.delete_message(chat_id=request.chat.id, message_id=result_message.message_id)
        except Exception as e:
            logger.error(f"User_id:{self.user_id} in Chat_id:{self.chat_id}: {e}")

    async def handle_button(self, bot, callback_query: types.CallbackQuery, action):
        chat_member = await bot.get_chat_member(self.chat_id, callback_query.from_user.id)
        if not ((chat_member.status == 'administrator' and chat_member.can_invite_users) or
                chat_member.status == 'creator'):
            await bot.answer_callback_query(callback_query.id, "You have no permission to do this.")
            return
        reply_msg = None
        edit_msg = None
        if action == "Approve":
            await self.request.approve()
            await bot.answer_callback_query(callback_query.id, "Approved.")
            edit_msg = f"{self.request.from_user.mention}(ID: {self.user_id}): Approved by {callback_query.from_user.mention}"
            reply_msg = "您已获批准加入\nYou have been approved."
            self.finished = True
        elif action == "Reject":
            await self.request.decline()
            await bot.answer_callback_query(callback_query.id, "Denied.")
            edit_msg = f"{self.request.from_user.mention}(ID: {self.user_id}): Denied by {callback_query.from_user.mention}"
            reply_msg = "您的申请已被拒绝。\nYou have been denied."
            self.finished = True
        elif action == "Ban":
            if chat_member.can_restrict_members or chat_member.status == 'creator':
                if self.bot_member.status == 'administrator' and self.bot_member.can_restrict_members:
                    await self.request.decline()
                    await bot.kick_chat_member(self.chat_id, self.user_id)
                    await bot.answer_callback_query(callback_query.id, "Banned.")
                    edit_msg = f"{self.request.from_user.mention}(ID: {self.user_id}): Banned by {callback_query.from_user.mention}"
                    reply_msg = "您已被封禁。\nYou have been banned."
                    self.finished = True
                else:
                    await self.request.decline()
                    await bot.answer_callback_query(callback_query.id, "Bot has no permission to ban.")
                    edit_msg = f"{self.request.from_user.mention}(ID: {self.user_id}): Denied by {callback_query.from_user.mention}"
                    reply_msg = "您的申请已被拒绝。\nYou have been denied."
                    self.finished = True
            else:
                await bot.answer_callback_query(callback_query.id, "You have no permission to ban.")
        else:
            await bot.answer_callback_query(callback_query.id, "Unknown action.")
            logger.error(f"Unknown action: {action}")

        if not self.finished:
            return
        if edit_msg:
            await self.notice_message.edit_text(edit_msg)
        try:
            if reply_msg:
                await self.user_message.reply(reply_msg)
        except Exception as e:
            logger.error(f"User_id:{self.user_id} in Chat_id:{self.chat_id}: {e}")
        await bot.stop_poll(self.chat_id, self.polling.message_id)
        await bot.delete_message(chat_id=self.chat_id, message_id=self.polling.message_id)
