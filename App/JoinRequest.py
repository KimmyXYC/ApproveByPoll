# -*- coding: utf-8 -*-
# @Time: 2023/11/4 20:00 
# @FileName: JoinRequest.py
# @Software: PyCharm
# @GitHub: KimmyXYC
import asyncio
from loguru import logger
from aiogram import types
from utils.Tool import cal_md5
from utils.LogChannel import log_c


class JoinRequest:
    def __init__(self, chat_id, user_id, bot_id, config):
        self.chat_id = chat_id
        self.user_id = user_id
        self.config = config
        self.finished = False

        self.bot_id = bot_id
        self.bot_member = None

        self.request = None
        self.user_message = None
        self.notice_message = None
        self.polling = None

    def check_up_status(self):
        return self.finished

    async def handle_join_request(self, bot, request: types.ChatJoinRequest, db):
        self.request = request
        self.bot_member = await bot.get_chat_member(self.chat_id, self.bot_id)

        # Log
        logger.info(f"New join request from {request.from_user.mention}(ID: {self.user_id}) in {self.chat_id}")
        await log_c(bot, request, "JoinRequest", self.config.log)

        chat_dict = db.get(str(self.chat_id))
        status_pin_msg = chat_dict.get("pin_msg", False)
        vote_time = chat_dict.get("vote_time", 600)

        # Time format
        minutes = vote_time // 60
        seconds = vote_time % 60
        if minutes == 0:
            _cn_time = f"{seconds}秒"
            _en_time = f"{seconds} seconds"
        elif seconds == 0:
            _cn_time = f"{minutes}分钟"
            _en_time = f"{minutes} minutes"
        else:
            _cn_time = f"{minutes}分钟{seconds}秒"
            _en_time = f"{minutes} minutes and {seconds} seconds"

        # Send message to user
        _zh_info = f"您正在申请加入「{request.chat.title}」，结果将于 {_cn_time} 后告知您。"
        _en_info = f"You are applying to join 「{request.chat.title}」. " \
                   f"The result will be communicated to you in {_en_time}."
        _info = f"请激活机器人以便告知您申请结果。\n" \
                f"Please activate the robot so that it can inform you of the application result."
        try:
            self.user_message = await bot.send_message(
                self.user_id,
                f"{_zh_info}\n{_en_info}\n\n{_info}",
            )
        except Exception as e:
            logger.error(f"Send message to User_id:{self.user_id}: {e}")

        # Buttons
        join_request_id = cal_md5(f"{self.chat_id}@{self.user_id}")
        keyboard = types.InlineKeyboardMarkup(row_width=3)
        approve_button = types.InlineKeyboardButton(text="Approve", callback_data=f"Approve {join_request_id}")
        reject_button = types.InlineKeyboardButton(text="Reject", callback_data=f"Reject {join_request_id}")
        ban_button = types.InlineKeyboardButton(text="Ban", callback_data=f"Ban {join_request_id}")
        keyboard.add(approve_button, reject_button, ban_button)

        notice_message = await bot.send_message(
            self.chat_id,
            f"{request.from_user.mention} (ID: {self.user_id}) is requesting to join this group."
            f"\n\ntg://user?id={self.user_id}",
            reply_markup=keyboard
        )
        self.notice_message = notice_message

        # Polling
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

        if status_pin_msg and self.bot_member.status == 'administrator' and self.bot_member.can_pin_messages:
            await bot.pin_chat_message(
                chat_id=self.chat_id,
                message_id=self.polling.message_id,
                disable_notification=True,
            )

        await asyncio.sleep(vote_time)

        # Check if the request has been processed
        if self.finished:
            return

        if status_pin_msg and self.bot_member.status == 'administrator' and self.bot_member.can_pin_messages:
            await bot.unpin_chat_message(
                chat_id=self.chat_id,
                message_id=self.polling.message_id,
            )

        # Get vote result
        vote_message = await bot.stop_poll(request.chat.id, self.polling.message_id)
        allow_count = vote_message.options[0].voter_count
        deny_count = vote_message.options[1].voter_count

        # Process the vote result
        if vote_message.total_voter_count == 0:
            logger.info(f"{self.user_id}: No one voted in {self.chat_id}")
            result_message = await notice_message.reply("No one voted.")
            approve_user = False
            edit_msg = f"{request.from_user.mention} (ID: {self.user_id}): No one voted."
            user_reply_msg = "无人投票，请稍后尝试重新申请。\nNo one voted. Please request again later."
        elif allow_count > deny_count:
            logger.info(f"{self.user_id}: Approved {self.user_id} in {self.chat_id}")
            result_message = await notice_message.reply("Approved.")
            approve_user = True
            edit_msg = f"{request.from_user.mention} (ID: {self.user_id}): Approved."
            user_reply_msg = "您已获批准加入\nYou have been approved."
        elif allow_count == deny_count:
            logger.info(f"{self.user_id}: Tie in {self.chat_id}")
            result_message = await notice_message.reply("Tie.")
            approve_user = False
            edit_msg = f"{request.from_user.mention} (ID: {self.user_id}): Tie."
            user_reply_msg = "平票，请稍后尝试重新申请。\nTie. Please request again later."
        else:
            logger.info(f"{self.user_id}: Denied {self.user_id} in {self.chat_id}")
            result_message = await notice_message.reply("Denied.")
            approve_user = False
            edit_msg = f"{request.from_user.mention} (ID: {self.user_id}): Denied."
            user_reply_msg = "您的申请已被拒绝。\nYou have been denied."

        # Process the request
        try:
            await notice_message.edit_text(edit_msg)
        except Exception as e:
            logger.error(f"Edit message in Chat_id:{self.chat_id}: {e}")
        try:
            await self.user_message.reply(user_reply_msg)
        except Exception as e:
            logger.error(f"Send message to User_id:{self.user_id}: {e}")
        try:
            if approve_user:
                await log_c(bot, request, "Approve_JoinRequest", self.config.log)
                await request.approve()
            else:
                await log_c(bot, request, "Decline_JoinRequest", self.config.log)
                await request.decline()
        except Exception as e:
            logger.error(f"Process request User_id:{self.user_id} in Chat_id:{self.chat_id}: {e}")
        self.finished = True

        await asyncio.sleep(60)

        # Clean up
        await bot.delete_message(chat_id=request.chat.id, message_id=self.polling.message_id)
        await bot.delete_message(chat_id=request.chat.id, message_id=result_message.message_id)

    async def handle_button(self, bot, callback_query: types.CallbackQuery, action):
        chat_member = await bot.get_chat_member(self.chat_id, callback_query.from_user.id)

        # Check permission
        if not ((chat_member.status == 'administrator' and chat_member.can_invite_users) or
                chat_member.status == 'creator'):
            await bot.answer_callback_query(callback_query.id, "You have no permission to do this.")
            return

        # Process the request
        if self.finished:
            await bot.answer_callback_query(callback_query.id, "This request has been processed")
            return
        if action == "Approve":
            self.finished = True
            approve_user = True
            await bot.answer_callback_query(callback_query.id, "Approved.")
            await log_c(bot, self.request, "Approve_JoinRequest", self.config.log, callback_query.from_user)
            edit_msg = f"{self.request.from_user.mention} (ID: {self.user_id}): " \
                       f"Approved by {callback_query.from_user.mention}"
            reply_msg = "您已获批准加入\nYou have been approved."
        elif action == "Reject":
            self.finished = True
            approve_user = False
            await bot.answer_callback_query(callback_query.id, "Denied.")
            await log_c(bot, self.request, "Decline_JoinRequest", self.config.log, callback_query.from_user)
            edit_msg = f"{self.request.from_user.mention} (ID: {self.user_id}): " \
                       f"Denied by {callback_query.from_user.mention}"
            reply_msg = "您的申请已被拒绝。\nYou have been denied."
        elif action == "Ban":
            if chat_member.can_restrict_members or chat_member.status == 'creator':
                if self.bot_member.status == 'administrator' and self.bot_member.can_restrict_members:
                    self.finished = True
                    approve_user = False
                    await bot.kick_chat_member(self.chat_id, self.user_id)
                    await bot.answer_callback_query(callback_query.id, "Banned.")
                    await log_c(bot, self.request, "Ban_JoinRequest", self.config.log, callback_query.from_user)
                    edit_msg = f"{self.request.from_user.mention} (ID: {self.user_id}): " \
                               f"Banned by {callback_query.from_user.mention}"
                    reply_msg = "您的申请已被拒绝。\nYou have been denied."
                else:
                    self.finished = True
                    approve_user = False
                    await bot.answer_callback_query(callback_query.id, "Bot has no permission to ban.")
                    await log_c(bot, self.request, "Decline_JoinRequest", self.config.log, callback_query.from_user)
                    edit_msg = f"{self.request.from_user.mention} (ID: {self.user_id}): " \
                               f"Denied by {callback_query.from_user.mention}"
                    reply_msg = "您的申请已被拒绝。\nYou have been denied."
            else:
                await bot.answer_callback_query(callback_query.id, "You have no permission to ban.")
                return
        else:
            await bot.answer_callback_query(callback_query.id, "Unknown action.")
            logger.error(f"Unknown action: {action}")
            return

        await self.notice_message.edit_text(edit_msg)
        try:
            await self.user_message.reply(reply_msg)
        except Exception as e:
            logger.error(f"Send message to User_id:{self.user_id}: {e}")
        try:
            if approve_user:
                await self.request.approve()
            else:
                await self.request.decline()
        except Exception as e:
            logger.error(f"Process request User_id:{self.user_id} in Chat_id:{self.chat_id}: {e}")

        # Clean up
        await bot.stop_poll(self.chat_id, self.polling.message_id)
        await bot.delete_message(chat_id=self.chat_id, message_id=self.polling.message_id)
