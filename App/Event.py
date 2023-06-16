# -*- coding: utf-8 -*-
# @Time： 2023/6/16 17:50 
# @FileName: Event.py
# @Software： PyCharm
# @GitHub: KimmyXYC
import asyncio
from loguru import logger
from aiogram import types


async def start(bot, message: types.Message, config):
    _url = "https://github.com/KimmyXYC/ApproveByPoll"
    _zh_info = f"这是一个用于投票加群的机器人。"
    _en_info = f"This is a Bot for voting to join the group."
    await message.reply(
        f"{_zh_info}\n{_en_info}\n\nOpen-source repository: {_url}",
        disable_web_page_preview=True,
    )


async def handle_join_request(bot, request: types.ChatJoinRequest, config):
    chat_id = request.chat.id
    user_id = request.from_user.id
    username = request.from_user.first_name
    logger.info(f"New join request from {username}(ID: {user_id}) in {chat_id}")
    _zh_info = f"您正在申请加入「{request.chat.title}」，结果将于5分钟后告知您。"
    _en_info = f"You are applying to join 「{request.chat.title}」. The result will be communicated to you in 5 minutes."
    _info = f"由于 Telegram 的限制，请按下 /start 以便机器人发送申请结果。\n" \
            f"Due to Telegram's restrictions, please press /start so that the bot can send the application result."
    user_message = await bot.send_message(
        user_id,
        f"{_zh_info}\n{_en_info}\n\n{_info}",
    )
    message = await bot.send_message(
        chat_id,
        f"{username}(ID: {user_id})申请入群。\n{username}(ID: {user_id}) is requesting to join this group.",
    )
    vote_question = f"是否允许其入群？/Approve this user?"
    vote_options = ["允许/Yes", "拒绝/No"]
    polling = await bot.send_poll(
        chat_id,
        vote_question,
        vote_options,
        is_anonymous=True,
        allows_multiple_answers=False,
        reply_to_message_id=message.message_id,
    )
    try:
        await bot.pin_chat_message(
            chat_id=chat_id,
            message_id=polling.message_id,
            disable_notification=True,
        )
    except Exception as e:
        logger.error(f"{chat_id}:{e}")
    await asyncio.sleep(300)
    try:
        await bot.unpin_chat_message(
            chat_id=chat_id,
            message_id=polling.message_id,
        )
    except Exception as e:
        logger.error(f"{chat_id}:{e}")
    try:
        vote_message = await bot.stop_poll(request.chat.id, polling.message_id)

        allow_count = vote_message.options[0].voter_count
        deny_count = vote_message.options[1].voter_count

        if vote_message.total_voter_count == 0:
            logger.info(f"{user_id}: No one voted in {chat_id}")
            result_message = await message.reply("无人投票。\nNo one voted.")
            await request.decline()
            await user_message.reply("无人投票，请稍后尝试重新申请。\nNo one voted. Please request again later.")
        elif allow_count > deny_count:
            logger.info(f"{user_id}: Approved {user_id} in {chat_id}")
            result_message = await message.reply("通过。\nApproved.")
            await request.approve()
            await user_message.reply("您已获批准加入\nYou have been approved.")
        elif allow_count == deny_count:
            logger.info(f"{user_id}: Tie in {chat_id}")
            result_message = await message.reply("平票。\nTie.")
            await request.decline()
            await user_message.reply("平票，请稍后尝试重新申请。\nTie. Please request again later.")
        else:
            logger.info(f"{user_id}: Denied {user_id} in {chat_id}")
            result_message = await message.reply("拒绝。\nDenied.")
            await request.decline()
            await user_message.reply("您的申请已被拒绝。\nYou have been denied.")
    except Exception as e:
        logger.error(f"User_id:{user_id}/Chat_id:{chat_id}: {e}")
    await asyncio.sleep(60)
    try:
        await bot.delete_message(chat_id=request.chat.id, message_id=message.message_id)
        await bot.delete_message(chat_id=request.chat.id, message_id=polling.message_id)
        await bot.delete_message(chat_id=request.chat.id, message_id=result_message.message_id)
    except Exception as e:
        logger.error(f"User_id:{user_id}/Chat_id:{chat_id}: {e}")
