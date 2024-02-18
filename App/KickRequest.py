# -*- coding: utf-8 -*-
# @Time: 2024/2/9 17:23 
# @FileName: KickRequest.py
# @Software: PyCharm
# @GitHub: KimmyXYC
import asyncio
from loguru import logger
from telebot import types
from utils.Tool import cal_md5


class Ostracism:
    def __init__(self, chat_id, initiator_user_id, target_user_id, bot_id):
        self.chat_id = chat_id
        self.bot_id = bot_id
        self.initiator_user_id = initiator_user_id
        self.target_user_id = target_user_id

        self.admin_status = False
        self.cancelled = False
        self.finished = False

        self.ostracism_id = None
        self.start_msg = None
        self.polling = None

        self.target_user_mention = None
        self.initiator_user_mention = None
        self.bot_member = None

    def check_up_status(self):
        return self.finished

    async def start_kick_vote(self, bot, message):
        self.bot_member = await bot.get_chat_member(self.chat_id, self.bot_id)
        try:
            target_user_member = await bot.get_chat_member(self.chat_id, self.target_user_id)
        except Exception as e:
            logger.error(f"User_id:{self.initiator_user_id} in Chat_id:{self.chat_id} want to kick ID:{self.target_user_id}: {e}")
            await bot.reply_to(message, "Cannot find the target user.")
            return
        if target_user_member.status == 'creator' or target_user_member.status == 'administrator':
            await bot.reply_to(message, "Cannot kick the administrator.")
            return
        elif target_user_member.status == 'none':
            await bot.reply_to(message, "Cannot find the target user.")
            return

        self.ostracism_id = cal_md5(f"{self.chat_id}@{int(self.target_user_id)}")

        self.initiator_user_mention = f'<a href="tg://user?id={self.initiator_user_id}">{message.from_user.first_name}'
        if message.from_user.last_name is not None:
            self.initiator_user_mention += f" {message.from_user.last_name}</a>"
        else:
            self.initiator_user_mention += "</a>"

        self.target_user_mention = f'<a href="tg://user?id={self.target_user_id}">{target_user_member.user.first_name}'
        if target_user_member.user.last_name is not None:
            self.target_user_mention += f" {target_user_member.user.last_name}</a>"
        else:
            self.target_user_mention += "</a>"

        buttons = types.InlineKeyboardMarkup()
        buttons.add(types.InlineKeyboardButton(text="Approve", callback_data=f"KR Approve {self.ostracism_id}"),
                    types.InlineKeyboardButton(text="Cancel", callback_data=f"KR Cancel {self.ostracism_id}"))
        self.start_msg = await bot.reply_to(
            message,
            f"{self.initiator_user_mention} want to start a kick voting to user {self.target_user_mention}.",
            reply_markup=buttons,
            parse_mode="HTML"
        )

        await asyncio.sleep(300)
        if not self.admin_status:
            await bot.edit_message_text(
                chat_id=self.chat_id,
                message_id=self.start_msg.message_id,
                text="No one approve this kick voting."
            )
        self.finished = True

    async def handle_button(self, bot, callback_query: types.CallbackQuery, action, db):
        chat_member = await bot.get_chat_member(self.chat_id, callback_query.from_user.id)
        if not callback_query.from_user.id == self.initiator_user_id:
            if not ((chat_member.status == 'administrator' and chat_member.can_restrict_members) or
                    chat_member.status == 'creator'):
                await bot.answer_callback_query(callback_query.id, "You have no permission to do this.")
                return
        admin_mention = f'<a href="tg://user?id={callback_query.from_user.id}">{callback_query.from_user.first_name}'
        if callback_query.from_user.last_name is not None:
            admin_mention += f" {callback_query.from_user.last_name}</a>"
        else:
            admin_mention += "</a>"
        if self.admin_status and action == "Approve":
            await bot.answer_callback_query(callback_query.id, "Admin have already done this.")
            return
        if action == "Approve":
            if callback_query.from_user.id == self.initiator_user_id:
                if not ((chat_member.status == 'administrator' and chat_member.can_restrict_members) or
                        chat_member.status == 'creator'):
                    await bot.answer_callback_query(callback_query.id, "You cannot approve your own request.")
                    return
            self.admin_status = True
        elif action == "Cancel":
            self.admin_status = True
            self.cancelled = True
            await bot.answer_callback_query(callback_query.id, "Canceled.")
            await bot.edit_message_text(
                chat_id=self.chat_id,
                message_id=self.start_msg.message_id,
                text=f"Kick voting to user {self.target_user_mention} was canceled by {admin_mention}.",
                parse_mode="HTML"
            )
            self.finished = True
            if self.polling:
                await bot.delete_message(chat_id=self.chat_id, message_id=self.polling.message_id)
            return
        else:
            await bot.answer_callback_query(callback_query.id, "Unknown action.")
            logger.error(f"Unknown action: {action}")
            return

        buttons = types.InlineKeyboardMarkup()
        buttons.add(types.InlineKeyboardButton(text="Cancel", callback_data=f"KR Cancel {self.ostracism_id}"))
        await bot.edit_message_text(
            chat_id=self.chat_id,
            message_id=self.start_msg.message_id,
            text=f"Start kick voting to user {self.target_user_mention}."
                 f"\nInitiator: {self.initiator_user_mention} Approver: {admin_mention}.",
            reply_markup=buttons,
            parse_mode="HTML"
        )

        chat_dict = db.get(str(self.chat_id))
        status_pin_msg = chat_dict.get("pin_msg", False)
        anonymous_vote = chat_dict.get("anonymous_vote", True)

        vote_question = "Kick out this user?"
        vote_options = ["Yes", "No"]
        self.polling = await bot.send_poll(
            self.chat_id,
            vote_question,
            vote_options,
            is_anonymous=anonymous_vote,
            allows_multiple_answers=False,
            reply_to_message_id=self.start_msg.message_id,
        )

        if status_pin_msg and self.bot_member.status == 'administrator' and self.bot_member.can_pin_messages:
            await bot.pin_chat_message(
                chat_id=self.chat_id,
                message_id=self.polling.message_id,
                disable_notification=True,
            )

        vote_time = chat_dict.get("vote_time", 600)
        await asyncio.sleep(vote_time)
        if self.cancelled:
            return
        if status_pin_msg and self.bot_member.status == 'administrator' and self.bot_member.can_pin_messages:
            await bot.unpin_chat_message(
                chat_id=self.chat_id,
                message_id=self.polling.message_id,
            )

        vote_message = await bot.stop_poll(self.chat_id, self.polling.message_id)
        allow_count = vote_message.options[0].voter_count
        deny_count = vote_message.options[1].voter_count

        if vote_message.total_voter_count == 0:
            logger.info(f"Ostracism {self.target_user_id}: No one voted in {self.chat_id}")
            result_message = await bot.reply_to(self.start_msg, "No one voted.")
            kick_user = False
            edit_msg = f"Kick {self.target_user_mention} (ID: <code>{self.target_user_id}</code>): No one voted."
        elif allow_count > deny_count:
            logger.info(f"Ostracism {self.target_user_id}: Kicking out in {self.chat_id}")
            result_message = await bot.reply_to(self.start_msg, "Kick out.")
            kick_user = True
            edit_msg = f"Kick {self.target_user_mention} (ID: <code>{self.target_user_id}</code>): Kick out."
        elif allow_count == deny_count:
            logger.info(f"Ostracism {self.target_user_id}: Tie in {self.chat_id}")
            result_message = await bot.reply_to(self.start_msg, "Tie.")
            kick_user = False
            edit_msg = f"Ostracism {self.target_user_mention} (ID: <code>{self.target_user_id}</code>): Tie."
        else:
            logger.info(f"Ostracism {self.target_user_id}: Not kicking out in {self.chat_id}")
            result_message = await bot.reply_to(self.start_msg, "Not kicking out")
            kick_user = False
            edit_msg = f"Ostracism {self.target_user_mention} (ID: <code>{self.target_user_id}</code>): Not kicking out."

        await bot.edit_message_text(
            chat_id=self.chat_id,
            message_id=self.start_msg.message_id,
            text=edit_msg,
            parse_mode="HTML"
        )

        if kick_user:
            await bot.kick_chat_member(self.chat_id, self.target_user_id)
            permissions = types.ChatPermissions(
                can_send_messages=True,
                can_send_media_messages=True,
                can_send_polls=True,
                can_send_other_messages=True,
                can_add_web_page_previews=True,
                can_change_info=True,
                can_invite_users=True,
                can_pin_messages=True
            )
            await bot.restrict_chat_member(self.chat_id, self.target_user_id, permissions=permissions)

        self.finished = True

        await asyncio.sleep(60)

        try:
            await bot.delete_message(chat_id=self.chat_id, message_id=self.polling.message_id)
            await bot.delete_message(chat_id=self.chat_id, message_id=result_message.message_id)
        except Exception as e:
            logger.error(f"User_id:{self.initiator_user_id} in Chat_id:{self.chat_id}: {e}")
