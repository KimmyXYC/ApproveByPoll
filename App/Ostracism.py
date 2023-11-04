# -*- coding: utf-8 -*-
# @Time: 2023/11/4 19:53 
# @FileName: Ostracism.py
# @Software: PyCharm
# @GitHub: KimmyXYC
import asyncio
from loguru import logger
from aiogram import types
from utils.Tool import calculate_md5


class Ostracism:
    def __init__(self, chat_id, user_id, target_id, bot_id):
        self.chat_id = chat_id
        self.user_id = user_id
        self.bot_id = bot_id
        self.target_id = target_id

        self.admin_status = False
        self.cancelled = False

        self.ostracism_id = None
        self.start_msg = None
        self.polling = None
        self.cmd_msg = None

        self.target_member = None
        self.bot_member = None

    async def start_ostracism(self, bot, message):
        self.cmd_msg = message
        self.bot_member = await bot.get_chat_member(self.chat_id, self.bot_id)
        try:
            self.target_member = await bot.get_chat_member(self.chat_id, self.target_id)
        except Exception as e:
            logger.error(f"User_id:{self.user_id} in Chat_id:{self.chat_id} want to Ostracism ID:{self.target_id}: {e}")
            await message.reply("Cannot find the target user.")
            return
        if self.target_member.status == 'creator' or self.target_member.status == 'administrator':
            await message.reply("Cannot kick the administrator.")
            return
        elif self.target_member.status == 'none':
            await message.reply("Cannot find the target user.")
            return

        self.ostracism_id = calculate_md5(f"{self.chat_id}@{self.user_id}@{int(self.target_id)}@Ostracism")
        keyboard = types.InlineKeyboardMarkup(row_width=2)
        approve_button = types.InlineKeyboardButton(
            text="Approve",
            callback_data=f"Ostracism/Approve/{self.ostracism_id}"
        )
        cancel_button = types.InlineKeyboardButton(
            text="Cancel",
            callback_data=f"Ostracism/Cancel/{self.ostracism_id}"
        )
        keyboard.add(approve_button, cancel_button)

        self.start_msg = await message.reply(
            f"{message.from_user.mention} want to start Ostracism voting to user {self.target_member.user.mention}."
            f"\n\nTarget User: tg://user?id={self.target_id}",
            reply_markup=keyboard
        )

        await asyncio.sleep(300)
        if not self.admin_status:
            await self.start_msg.edit_text("No one approve this Ostracism.")

    async def handle_button(self, bot, callback_query: types.CallbackQuery, action, db):
        chat_member = await bot.get_chat_member(self.chat_id, callback_query.from_user.id)
        if not callback_query.from_user.id == self.user_id:
            if not ((chat_member.status == 'administrator' and chat_member.can_restrict_members) or
                    chat_member.status == 'creator'):
                await bot.answer_callback_query(callback_query.id, "You have no permission to do this.")
                return
        if self.admin_status and action == "Approve":
            await bot.answer_callback_query(callback_query.id, "Admin have already done this.")
            return
        if action == "Approve":
            if callback_query.from_user.id == self.user_id:
                if not ((chat_member.status == 'administrator' and chat_member.can_restrict_members) or
                        chat_member.status == 'creator'):
                    await bot.answer_callback_query(callback_query.id, "You cannot approve your own request.")
                    return
            self.admin_status = True
        elif action == "Cancel":
            self.admin_status = True
            self.cancelled = True
            await bot.answer_callback_query(callback_query.id, "Canceled.")
            await self.start_msg.edit_text(
                f"Ostracism voting to user {self.target_member.user.mention} was canceled "
                f"by {callback_query.from_user.mention}."
            )
            if self.polling:
                await bot.delete_message(chat_id=self.chat_id, message_id=self.polling.message_id)
            return
        else:
            await bot.answer_callback_query(callback_query.id, "Unknown action.")
            logger.error(f"Unknown action: {action}")
            return

        keyboard = types.InlineKeyboardMarkup(row_width=1)
        cancel_button = types.InlineKeyboardButton(
            text="Cancel",
            callback_data=f"Ostracism/Cancel/{self.ostracism_id}"
        )
        keyboard.add(cancel_button)
        await self.start_msg.edit_text(
            f"Start Ostracism voting to user {self.target_member.user.mention}."
            f"\nInitiator: {self.cmd_msg.from_user.mention} Approver: {callback_query.from_user.mention}."
            f"\n\nTarget User: tg://user?id={self.target_id}",
            reply_markup=keyboard
        )

        vote_question = "Kick out this user?"
        vote_options = ["Yes", "No"]
        self.polling = await bot.send_poll(
            self.chat_id,
            vote_question,
            vote_options,
            is_anonymous=True,
            allows_multiple_answers=False,
            reply_to_message_id=self.start_msg.message_id,
        )

        chat_dict = db.get(str(self.chat_id))
        status_pin_msg = chat_dict.get("pin_msg", False)

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
            logger.info(f"Ostracism {self.target_id}: No one voted in {self.chat_id}")
            result_message = await self.start_msg.reply("No one voted.")
            kick_user = False
            edit_msg = f"Ostracism {self.target_member.user.mention} (ID: {self.target_id}): No one voted."
        elif allow_count > deny_count:
            logger.info(f"Ostracism {self.target_id}: Kick {self.user_id} in {self.chat_id}")
            result_message = await self.start_msg.reply("Kick out.")
            kick_user = True
            edit_msg = f"Ostracism {self.target_member.user.mention} (ID: {self.target_id}): Kick out."
        elif allow_count == deny_count:
            logger.info(f"Ostracism {self.target_id}: Tie in {self.chat_id}")
            result_message = await self.start_msg.reply("Tie.")
            kick_user = False
            edit_msg = f"Ostracism {self.target_member.user.mention} (ID: {self.target_id}): Tie."
        else:
            logger.info(f"Ostracism {self.target_id}: Don't kick out {self.user_id} in {self.chat_id}")
            result_message = await self.start_msg.reply("Don't kick out.")
            kick_user = False
            edit_msg = f"Ostracism {self.target_member.user.mention} (ID: {self.target_id}): Don't kick out."

        await self.start_msg.edit_text(edit_msg)

        if kick_user:
            await bot.kick_chat_member(self.chat_id, self.target_id)
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
            await bot.restrict_chat_member(self.chat_id, self.target_id, permissions=permissions)

        await asyncio.sleep(60)

        try:
            await bot.delete_message(chat_id=self.chat_id, message_id=self.polling.message_id)
            await bot.delete_message(chat_id=self.chat_id, message_id=result_message.message_id)
        except Exception as e:
            logger.error(f"User_id:{self.user_id} in Chat_id:{self.chat_id}: {e}")
