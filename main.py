import asyncio
import logging
import os

from aiogram import Bot, Dispatcher, executor, types

logging.basicConfig(level=logging.INFO)
bot = Bot(token=os.getenv("TOKEN"))
dp = Dispatcher(bot)


@dp.message_handler(commands=['start'])
async def send_welcome(message: types.Message):
	await message.reply("我是你爹")


@dp.chat_join_request_handler()
async def join(request: types.ChatJoinRequest):
	userid = request.from_user.id
	username = request.from_user.username
	logging.info(f"{username}({userid}) is requesting to join this group.")
	message = await bot.send_message(request.chat.id, f"@{username}({userid}) is requesting to join this group.")
	polling = await bot.send_poll(
		request.chat.id,
		"Approve this user?",
		["Yes", "No"],
		is_anonymous=True,
		allows_multiple_answers=False,
		reply_to_message_id=message.message_id,
	)
	await asyncio.sleep(300)
	polling = await bot.stop_poll(request.chat.id, polling.message_id)

	if polling.total_voter_count == 0:
		await message.reply("No one voted.")
		await bot.send_message(userid, "No one voted. Please request again later.")
		await request.decline()
	elif polling.options[0].voter_count > polling.options[1].voter_count:
		await message.reply("Approved.")
		await bot.send_message(userid, "You have been approved.")
		await request.approve()
	elif polling.options[0].voter_count == polling.options[1].voter_count:
		await message.reply("Tie.")
		await bot.send_message(userid, "Tie. Please request again later.")
		await request.decline()
	else:
		await message.reply("Denied.")
		await bot.send_message(userid, "You have been denied.")
		await request.decline()


if __name__ == '__main__':
	executor.start_polling(dp)
