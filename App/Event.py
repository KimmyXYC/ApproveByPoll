# -*- coding: utf-8 -*-
# @Time： 2023/6/16 17:50 
# @FileName: Event.py
# @Software： PyCharm
# @GitHub: KimmyXYC
import asyncio
from loguru import logger
from aiogram import types
from utils.Tool import calculate_md5


async def start(bot, message: types.Message, config):
    _url = "https://github.com/KimmyXYC/ApproveByPoll"
    _zh_info = f"这是一个用于投票加群的机器人。\n机器人必须拥有邀请，封禁，发起投票权限。"
    _en_info = f"This is a Bot for voting to join the group.\nBot must have invite, ban and poll permissions."
    await message.reply(
        f"{_zh_info}\n{_en_info}\n\nOpen-source repository: {_url}",
        disable_web_page_preview=True,
    )


async def delete_pinned_message(bot, message: types.Message):
    bot_user = await bot.get_me()
    bot_member = await bot.get_chat_member(message.chat.id, bot_user.id)
    if bot_member.status == 'administrator' and bot_member.can_delete_messages:
        try:
            await message.delete()
        except Exception as e:
            logger.error(f"Delete pinned message failed: {e}")


class JoinRequest:
    def __init__(self):
        self.user_mention = None
        self.polling = None
        self.user_message = None
        self.notice_message = None
        self.request = None
        self.chat_id = None
        self.user_id = None
        self.finished = False

    async def handle_join_request(self, bot, request: types.ChatJoinRequest, config):
        chat_id = request.chat.id
        user_id = request.from_user.id
        self.chat_id = chat_id
        self.user_id = user_id
        self.request = request

        bot_user = await bot.get_me()
        bot_member = await bot.get_chat_member(self.chat_id, bot_user.id)
        user_mention = request.from_user.mention
        self.user_mention = user_mention
        logger.info(f"New join request from {user_mention}(ID: {user_id}) in {chat_id}")

        _zh_info = f"您正在申请加入「{request.chat.title}」，结果将于5分钟后告知您。"
        _en_info = f"You are applying to join 「{request.chat.title}」. " \
                   f"The result will be communicated to you in 5 minutes."
        _info = f"由于 Telegram 的限制，首次使用请按下 /start 以便机器人发送申请结果。\n" \
                f"Due to limitations imposed by Telegram, " \
                f"please press /start for the first time to allow the bot to send the application result."
        user_message = await bot.send_message(
            user_id,
            f"{_zh_info}\n{_en_info}\n\n{_info}",
        )
        self.user_message = user_message

        join_request_id = calculate_md5(f"{chat_id}@{user_id}")
        keyboard = types.InlineKeyboardMarkup(row_width=3)
        approve_button = types.InlineKeyboardButton(text="通过", callback_data=f"approve/{join_request_id}")
        reject_button = types.InlineKeyboardButton(text="拒绝", callback_data=f"reject/{join_request_id}")
        ban_button = types.InlineKeyboardButton(text="封禁", callback_data=f"ban/{join_request_id}")
        keyboard.add(approve_button, reject_button, ban_button)

        notice_message = await bot.send_message(
            chat_id,
            f"{user_mention}(ID: {user_id})申请入群。"
            f"\n{user_mention}(ID: {user_id}) is requesting to join this group."
            f"\n\n tg://user?id={user_id}",
            reply_markup=keyboard
        )
        self.notice_message = notice_message

        vote_question = f"是否允许其入群？/Approve this user?"
        vote_options = ["允许/Yes", "拒绝/No"]
        polling = await bot.send_poll(
            chat_id,
            vote_question,
            vote_options,
            is_anonymous=True,
            allows_multiple_answers=False,
            reply_to_message_id=notice_message.message_id,
        )
        self.polling = polling

        if bot_member.status == 'administrator' and bot_member.can_pin_messages:
            await bot.pin_chat_message(
                chat_id=chat_id,
                message_id=polling.message_id,
                disable_notification=True,
            )

        await asyncio.sleep(300)

        result_message = None
        reply_msg = None
        edit_msg = None

        if not self.finished:
            if bot_member.status == 'administrator' and bot_member.can_pin_messages:
                await bot.unpin_chat_message(
                    chat_id=chat_id,
                    message_id=polling.message_id,
                )

            try:
                vote_message = await bot.stop_poll(request.chat.id, polling.message_id)

                allow_count = vote_message.options[0].voter_count
                deny_count = vote_message.options[1].voter_count

                if vote_message.total_voter_count == 0:
                    logger.info(f"{user_id}: No one voted in {chat_id}")
                    result_message = await notice_message.reply("无人投票。\nNo one voted.")
                    await request.decline()
                    edit_msg = f"{user_mention}(ID: {user_id}) 无人投票。" \
                               f"\n{user_mention}(ID: {user_id}) No one voted."
                    reply_msg = "无人投票，请稍后尝试重新申请。\nNo one voted. Please request again later."
                elif allow_count > deny_count:
                    logger.info(f"{user_id}: Approved {user_id} in {chat_id}")
                    result_message = await notice_message.reply("通过。\nApproved.")
                    await request.approve()
                    edit_msg = f"{user_mention}(ID: {user_id}) 已通过。" \
                               f"\n{user_mention}(ID: {user_id}) Approved."
                    reply_msg = "您已获批准加入\nYou have been approved."
                elif allow_count == deny_count:
                    logger.info(f"{user_id}: Tie in {chat_id}")
                    result_message = await notice_message.reply("平票。\nTie.")
                    await request.decline()
                    edit_msg = f"{user_mention}(ID: {user_id}) 平票。" \
                               f"\n{user_mention}(ID: {user_id}) Tie."
                    reply_msg = "平票，请稍后尝试重新申请。\nTie. Please request again later."
                else:
                    logger.info(f"{user_id}: Denied {user_id} in {chat_id}")
                    result_message = await notice_message.reply("拒绝。\nDenied.")
                    await request.decline()
                    edit_msg = f"{user_mention}(ID: {user_id}) 已拒绝。" \
                               f"\n{user_mention}(ID: {user_id}) Denied."
                    reply_msg = "您的申请已被拒绝。\nYou have been denied."
            except Exception as e:
                logger.error(f"User_id:{user_id} in Chat_id:{chat_id}: {e}")

            if edit_msg:
                await notice_message.edit_text(edit_msg)
            try:
                if reply_msg:
                    await user_message.reply(reply_msg)
            except Exception as e:
                logger.error(f"Send message to User_id:{user_id}: {e}")

            await asyncio.sleep(60)

            try:
                await bot.delete_message(chat_id=request.chat.id, message_id=polling.message_id)
                if result_message:
                    await bot.delete_message(chat_id=request.chat.id, message_id=result_message.message_id)
            except Exception as e:
                logger.error(f"User_id:{user_id}/Chat_id:{chat_id}: {e}")

    async def handle_button(self, bot, callback_query: types.CallbackQuery, action):
        chat_member = await bot.get_chat_member(self.chat_id, callback_query.from_user.id)
        if (chat_member.status == 'administrator' and chat_member.can_invite_users) \
                or chat_member.status == 'creator':
            reply_msg = None
            edit_msg = None
            if action == "approve":
                await self.request.approve()
                await bot.answer_callback_query(callback_query.id, "已通过。Approved.")
                edit_msg = f"{self.user_mention}(ID: {self.user_id})的申请已被批准。\n" \
                           f"{self.user_mention}(ID: {self.user_id})'s request has been approved by {callback_query.from_user.mention}"
                reply_msg = "您已获批准加入\nYou have been approved."
                self.finished = True
            elif action == "reject":
                await self.request.decline()
                await bot.answer_callback_query(callback_query.id, "已拒绝。Denied.")
                edit_msg = f"{self.user_mention}(ID: {self.user_id})的申请已被拒绝。\n" \
                           f"{self.user_mention}(ID: {self.user_id})'s request has been denied by {callback_query.from_user.mention}"
                reply_msg = "您的申请已被拒绝。\nYou have been denied."
                self.finished = True
            elif action == "ban":
                if chat_member.can_restrict_members or chat_member.status == 'creator':
                    bot_user = await bot.get_me()
                    bot_member = await bot.get_chat_member(self.chat_id, bot_user.id)
                    if bot_member.status == 'administrator' and bot_member.can_restrict_members:
                        await self.request.decline()
                        await bot.kick_chat_member(self.chat_id, self.user_id)
                        await bot.answer_callback_query(callback_query.id, "已封禁。Banned.")
                        edit_msg = f"{self.user_mention}(ID: {self.user_id})已被封禁。\n" \
                                   f"{self.user_mention}(ID: {self.user_id}) has been banned by {callback_query.from_user.mention}"
                        reply_msg = "您已被封禁。\nYou have been banned."
                        self.finished = True
                    else:
                        await self.request.decline()
                        await bot.answer_callback_query(callback_query.id, "机器人无权限封禁。Bot has no permission to ban.")
                        edit_msg = f"{self.user_mention}(ID: {self.user_id})的申请已被拒绝。\n" \
                                   f"{self.user_mention}(ID: {self.user_id})'s request has been denied by {callback_query.from_user.mention}"
                        reply_msg = "您的申请已被拒绝。\nYou have been denied."
                        self.finished = True
                else:
                    await bot.answer_callback_query(callback_query.id, "您无权封禁。You have no permission to ban.")
            else:
                await bot.answer_callback_query(callback_query.id, "未知操作。Unknown action.")

            if self.finished:
                if edit_msg:
                    await self.notice_message.edit_text(edit_msg)
                try:
                    if reply_msg:
                        await self.user_message.reply(reply_msg)
                except Exception as e:
                    logger.error(f"User_id:{self.user_id} in Chat_id:{self.chat_id}: {e}")
                await bot.stop_poll(self.chat_id, self.polling.message_id)
                await bot.delete_message(chat_id=self.chat_id, message_id=self.polling.message_id)
        else:
            await bot.answer_callback_query(callback_query.id, "您无权操作。You have no permission to do this.")
