# -*- coding: utf-8 -*-
# @Time: 2023/11/4 20:00 
# @FileName: JoinRequest.py
# @Software: PyCharm
# @GitHub: KimmyXYC
import asyncio
import gettext
from loguru import logger
from telebot import types
from utils.Tool import cal_md5
from utils.LogChannel import log_c

_ = gettext.gettext


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

        self.user_mention = None

    def check_up_status(self):
        return self.finished 

    async def handle_join_request(self, bot, request: types.ChatJoinRequest, db):
        self.request = request
        self.bot_member = await bot.get_chat_member(self.chat_id, self.bot_id)

        if request.from_user.username is not None:
            self.user_mention = f'@{request.from_user.username}'
        else:
            self.user_mention = f'<a href="tg://user?id={self.user_id}">{request.from_user.first_name}'
            if request.from_user.last_name is not None:
                self.user_mention += f" {request.from_user.last_name}</a>"
            else:
                self.user_mention += "</a>"

        # Log
        logger.info(f"New join request from {request.from_user.first_name}(ID: {self.user_id}) in {self.chat_id}")
        await log_c(bot, request, "JoinRequest", self.config.log)

        chat_dict = db.get(str(self.chat_id))
        if chat_dict is None:
            chat_dict = {}
        status_pin_msg = chat_dict.get("pin_msg", False)
        vote_time = chat_dict.get("vote_time", 600)
        anonymous_vote = chat_dict.get("anonymous_vote", True)

        # Time format
        minutes = vote_time // 60
        seconds = vote_time % 60
        if minutes == 0:
            _time = _("{} seconds").format(seconds)
        elif seconds == 0:
            _time = _("{} minutes").format(minutes)
        else:
            _time = _("{} minutes and {} seconds").format(minutes, seconds)

        # Send message to user
        _info = _("You are applying to join 「{}」. The result will be communicated to you in {}.").format(
            request.chat.title, _time)

        try:
            self.user_message = await bot.send_message(
                self.user_id,
                f"{_info}",
            )
        except Exception as e:
            logger.error(f"Send message to User_id:{self.user_id}: {e}")

        # Buttons
        join_request_id = cal_md5(f"{self.chat_id}@{self.user_id}")
        keyboard = types.InlineKeyboardMarkup(row_width=3)
        approve_button = types.InlineKeyboardButton(text=_("Approve"), callback_data=f"JR Approve {join_request_id}")
        reject_button = types.InlineKeyboardButton(text=_("Reject"), callback_data=f"JR Reject {join_request_id}")
        ban_button = types.InlineKeyboardButton(text=_("Ban"), callback_data=f"JR Ban {join_request_id}")
        keyboard.add(approve_button, reject_button, ban_button)

        notice_message_text = _("{} (ID: <code>{}</code>) is requesting to join this group.").format(
            self.user_mention, self.user_id)
        if request.from_user.username is None:
            link = f"tg://user?id={self.user_id}"
            notice_message_text += "\n\n"
            notice_message_text += _("Alternate Link: {}").format(link)

        notice_message = await bot.send_message(
            self.chat_id,
            notice_message_text,
            reply_markup=keyboard,
            parse_mode="HTML"
        )
        self.notice_message = notice_message

        # Polling
        vote_question = _("Approve this user?")
        vote_options = [_("Yes"), _("No")]
        self.polling = await bot.send_poll(
            self.chat_id,
            vote_question,
            vote_options,
            is_anonymous=anonymous_vote,
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
            result_message = bot.reply_to(notice_message, _("No one voted."))
            approve_user = False
            edit_msg = _("{} (ID: <code>{}</code>): No one voted.").format(self.user_mention, self.user_id)
            user_reply_msg = _("No one voted. Please request again later.")
        elif allow_count > deny_count:
            logger.info(f"{self.user_id}: Approved in {self.chat_id}")
            result_message = await bot.reply_to(notice_message, _("Approved."))
            approve_user = True
            edit_msg = _("{} (ID: <code>{}</code>): Approved.").format(self.user_mention, self.user_id)
            user_reply_msg = _("You have been approved.")
        elif allow_count == deny_count:
            logger.info(f"{self.user_id}: Tie in {self.chat_id}")
            result_message = await bot.reply_to(notice_message, _("Tie."))
            approve_user = False
            edit_msg = _("{} (ID: <code>{}</code>): Tie.").format(self.user_mention, self.user_id)
            user_reply_msg = _("Tie. Please request again later.")
        else:
            logger.info(f"{self.user_id}: Denied in {self.chat_id}")
            result_message = await bot.reply_to(notice_message, _("Denied."))
            approve_user = False
            edit_msg = _("{} (ID: <code>{}</code>): Denied.").format(self.user_mention, self.user_id)
            user_reply_msg = _("You have been denied.")

        # Process the request
        try:
            await bot.edit_message_text(edit_msg, chat_id=self.chat_id, message_id=notice_message.message_id, parse_mode="HTML")
        except Exception as e:
            logger.error(f"Edit message in Chat_id:{self.chat_id}: {e}")
        try:
            await bot.reply_to(self.user_message, user_reply_msg)
        except Exception as e:
            logger.error(f"Send message to User_id:{self.user_id}: {e}")
        try:
            if approve_user:
                await log_c(bot, request, "Approve_JoinRequest", self.config.log)
                await bot.approve_chat_join_request(request.chat.id, request.from_user.id)
            else:
                await log_c(bot, request, "Decline_JoinRequest", self.config.log)
                await bot.decline_chat_join_request(request.chat.id, request.from_user.id)
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
            await bot.answer_callback_query(callback_query.id, _("You have no permission to do this."))
            return

        # Process the request
        if self.finished:
            await bot.answer_callback_query(callback_query.id, _("This request has been processed"))
            return

        admin_mention = f'<a href="tg://user?id={callback_query.from_user.id}">{callback_query.from_user.first_name}'
        if callback_query.from_user.last_name is not None:
            admin_mention += f" {callback_query.from_user.last_name}</a>"
        else:
            admin_mention += "</a>"

        if action == "Approve":
            self.finished = True
            approve_user = True
            await bot.answer_callback_query(callback_query.id, _("Approved."))
            logger.info(f"{self.user_id}: Approved by {callback_query.from_user.id} in {self.chat_id}")
            await log_c(bot, self.request, "Approve_JoinRequest", self.config.log, admin_mention)
            edit_msg = _("{} (ID: <code>{}</code>): Approved by {}").format(
                self.user_mention, self.user_id, admin_mention)
            reply_msg = _("Your application have been approved.")
        elif action == "Reject":
            self.finished = True
            approve_user = False
            await bot.answer_callback_query(callback_query.id, _("Denied."))
            logger.info(f"{self.user_id}: Denied by {callback_query.from_user.id} in {self.chat_id}")
            await log_c(bot, self.request, "Decline_JoinRequest", self.config.log, admin_mention)
            edit_msg = _("{} (ID: <code>{}</code>): Denied by {}").format(
                self.user_mention, self.user_id, admin_mention)
            reply_msg = _("Your application have been denied.")
        elif action == "Ban":
            if chat_member.can_restrict_members or chat_member.status == 'creator':
                if self.bot_member.status == 'administrator' and self.bot_member.can_restrict_members:
                    self.finished = True
                    approve_user = False
                    await bot.kick_chat_member(self.chat_id, self.user_id)
                    await bot.answer_callback_query(callback_query.id, "Banned.")
                    logger.info(f"{self.user_id}: Banned by {callback_query.from_user.id} in {self.chat_id}")
                    await log_c(bot, self.request, "Ban_JoinRequest", self.config.log, admin_mention)
                    edit_msg = _("{} (ID: <code>{}</code>): Banned by {}").format(
                        self.user_mention, self.user_id, admin_mention)
                    reply_msg = _("Your application have been denied.")
                else:
                    self.finished = True
                    approve_user = False
                    await bot.answer_callback_query(callback_query.id, _("Bot has no permission to ban."))
                    logger.info(f"{self.user_id}: Denied by {callback_query.from_user.id} in {self.chat_id}")
                    await log_c(bot, self.request, "Decline_JoinRequest", self.config.log, admin_mention)
                    edit_msg = _("{} (ID: <code>{}</code>): Denied by {}").format(
                        self.user_mention, self.user_id, admin_mention)
                    reply_msg = _("Your application have been denied.")
            else:
                await bot.answer_callback_query(callback_query.id, _("You have no permission to ban."))
                return
        else:
            await bot.answer_callback_query(callback_query.id, "Unknown action.")
            logger.error(f"Unknown action: {action}")
            return

        await bot.edit_message_text(edit_msg, chat_id=self.chat_id, message_id=self.notice_message.message_id, parse_mode="HTML")
        try:
            await bot.reply_to(self.user_message, reply_msg)
        except Exception as e:
            logger.error(f"Send message to User_id:{self.user_id}: {e}")
        try:
            if approve_user:
                await bot.approve_chat_join_request(self.request.chat.id, self.request.from_user.id)
            else:
                await bot.decline_chat_join_request(self.request.chat.id, self.request.from_user.id)
        except Exception as e:
            logger.error(f"Process request User_id:{self.user_id} in Chat_id:{self.chat_id}: {e}")

        # Clean up
        await bot.stop_poll(self.chat_id, self.polling.message_id)
        await bot.delete_message(chat_id=self.chat_id, message_id=self.polling.message_id)
