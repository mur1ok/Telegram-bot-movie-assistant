import os
from aiogram import Bot, types
from aiogram.dispatcher import Dispatcher
from aiogram.utils import executor
from aiogram.types import ParseMode
from parser import RequestParser
from databse import DataBaseHandler

bot = Bot(token=os.environ['BOT_TOKEN'])
dp = Dispatcher(bot)

db = DataBaseHandler("tgbot_stats.db")
parser = RequestParser()


async def send_formatted_message(row_user_request: str, message: types.Message) -> None:
    """
    Searches for information on a user request, generates a response text and sends it to a chat with the user.
    :param row_user_request:
    :param message:
    :return:
    """
    result = await parser.take_formatted_message(row_user_request, message.from_user.username, db)
    await message.answer(result, parse_mode=ParseMode.HTML)


@dp.message_handler(commands=['start'])
async def send_welcome(message: types.Message) -> None:
    await message.answer("А теперь давай начинать, что бы ты хотел посмотреть? 🙂")


@dp.message_handler(commands=['help'])
async def send_help(message: types.Message) -> None:
    await message.answer("Я помогаю находить нужные фильмы на куче разных площадок,"
                         " а тебе только останется выбрать самую удобную.\n"
                         "Введи команду <b>/stats</b>, и я покажу какие фильмы я предлагал тебе к просмотру. "
                         "Чтобы тебе было удобно, я отсортировал их по частоте показа.\n"
                         "Когда захочешь вспомнить, какие фильмы ты уже искал введи команду <b>/history</b>, "
                         "вместо того, чтобы пролистывать весь диалог.", parse_mode=ParseMode.HTML)


@dp.message_handler(commands=['history'])
async def send_history(message: types.Message) -> None:
    """
    Gets query statistics for a given user and sends it to the chat
    """
    hist: list[tuple[str]] = db.get_user_history(message.from_user.username)
    if not hist:
        await message.answer("<b>Кажется ты еще ничего у меня не спрашивал, не так ли? 😉</b>",
                             parse_mode=ParseMode.HTML)
        return None
    result = "<b>Вот какие фильмы я помогал тебе искать:</b>\n"
    for i, film in enumerate(hist):
        result += f"{i + 1}) {film[0]}\n"
    await message.answer(result, parse_mode=ParseMode.HTML)


@dp.message_handler(commands=['stats'])
async def send_stats(message: types.Message) -> None:
    """
    Retrieves the impression statistics for the given user and sends them to the chat in descending sorted order
    """
    stats: list[tuple[str, int]] = db.get_user_stats(message.from_user.username)
    if not stats:
        await message.answer("<b>Чтобы показать статистику, "
                             "я должен тебе предложить хотя бы один фильм 😉</b>", parse_mode=ParseMode.HTML)
        return None
    stats.sort(key=(lambda x: x[1]), reverse=True)
    result = "<b>Вот какие фильмы я предлагал тебе посмотреть:</b>\n"
    for i, (film, showing) in enumerate(stats):
        result += f"{i + 1}) {film} - {showing} раз(а)\n"
    await message.answer(result, parse_mode=ParseMode.HTML)


@dp.message_handler()
async def take_cinema_name(message: types.Message) -> None:
    await send_formatted_message(message.text, message)


if __name__ == '__main__':
    executor.start_polling(dp)
