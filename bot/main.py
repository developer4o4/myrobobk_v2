import asyncio
import logging
import os

import aiohttp
from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart
from aiogram.types import KeyboardButton, ReplyKeyboardMarkup

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.environ["BOT_TOKEN"]
API_URL = os.environ["API_URL"]
BOT_SECRET = os.environ["BOT_OTP_SECRET"]

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

contact_keyboard = ReplyKeyboardMarkup(
    keyboard=[[KeyboardButton(text="📱 Telefon yuborish", request_contact=True)]],
    resize_keyboard=True,
    one_time_keyboard=True,
)


@dp.message(CommandStart())
async def cmd_start(message: types.Message):
    await message.answer(
        "Saytga kirish uchun telefon raqamingizni yuboring:",
        reply_markup=contact_keyboard,
    )


@dp.message(lambda m: m.contact is not None)
async def contact_handler(message: types.Message):
    phone = message.contact.phone_number
    username = message.from_user.username or ""

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                API_URL,
                json={"phone": phone, "username": username},
                headers={"X-BOT-SECRET": BOT_SECRET},
                timeout=aiohttp.ClientTimeout(total=10),
            ) as resp:
                if resp.status != 200:
                    text = await resp.text()
                    logger.error("API error %s: %s", resp.status, text)
                    await message.answer("Xatolik yuz berdi. Qayta urinib ko'ring.")
                    return

                data = await resp.json()

        code = data.get("code")
        expires = data.get("expires_in_min", 3)

        await message.answer(
            f"🔑 Saytga kirish uchun kod:\n\n"
            f"<code>{code}</code>\n\n"
            f"⏱ Kod {expires} daqiqa davomida amal qiladi.",
            parse_mode="HTML",
            reply_markup=types.ReplyKeyboardRemove(),
        )

    except aiohttp.ClientConnectorError:
        logger.exception("API ga ulanib bo'lmadi")
        await message.answer("Server bilan aloqa yo'q. Biroz kutib, qayta urinib ko'ring.")
    except Exception:
        logger.exception("contact_handler xatosi")
        await message.answer("Kutilmagan xato yuz berdi.")


async def main():
    logger.info("Bot ishga tushmoqda...")
    await dp.start_polling(bot, skip_updates=True)


if __name__ == "__main__":
    asyncio.run(main())
