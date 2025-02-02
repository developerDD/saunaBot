import logging
import asyncio
import os
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

# Отримуємо API-токен з змінних середовища
API_TOKEN = os.getenv("TELEGRAM_API_TOKEN")

# Логування
logging.basicConfig(level=logging.INFO)

# Ініціалізація бота та диспетчера
bot = Bot(token=API_TOKEN)
dp = Dispatcher()

# Головне меню
main_menu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="➕ Додати користувача")],
        [KeyboardButton(text="❌ Видалити користувача")],
        [KeyboardButton(text="💰 Додати витрати")],
        [KeyboardButton(text="📊 Розрахувати витрати")]
    ],
    resize_keyboard=True
)

# Тимчасове сховище користувачів та витрат (замінити на Google Sheets/БД)
users = {}
expenses = []

@dp.message(Command("start"))
async def start(message: types.Message):
    await message.answer("Привіт! Я бот для розрахунку витрат на баню. Вибери дію:", reply_markup=main_menu)

@dp.message(lambda message: message.text == "➕ Додати користувача")
async def add_user(message: types.Message):
    user_id = message.from_user.id
    users[user_id] = message.from_user.full_name
    await message.answer(f"✅ Користувач {message.from_user.full_name} доданий!")

@dp.message(lambda message: message.text == "❌ Видалити користувача")
async def remove_user(message: types.Message):
    user_id = message.from_user.id
    if user_id in users:
        del users[user_id]
        await message.answer("❌ Ви видалені зі списку!")
    else:
        await message.answer("⚠️ Вас немає в списку!")

@dp.message(lambda message: message.text == "💰 Додати витрати")
async def add_expense(message: types.Message):
    await message.answer("Введіть суму витрат і категорію (їжа/алкоголь/баня) у форматі: 500 їжа")

@dp.message(lambda message: " " in message.text)
async def save_expense(message: types.Message):
    try:
        amount, category = message.text.split()
        amount = float(amount)
        expenses.append({"user": message.from_user.full_name, "amount": amount, "category": category})
        await message.answer(f"✅ Витрата {amount} грн на {category} додана!")
    except:
        await message.answer("⚠️ Невірний формат! Введіть суму та категорію через пробіл, наприклад: 500 їжа")

@dp.message(lambda message: message.text == "📊 Розрахувати витрати")
async def calculate_expenses(message: types.Message):
    total = sum(exp["amount"] for exp in expenses)
    food = sum(exp["amount"] for exp in expenses if exp["category"] == "їжа")
    alcohol = sum(exp["amount"] for exp in expenses if exp["category"] == "алкоголь")
    bath = sum(exp["amount"] for exp in expenses if exp["category"] == "баня")

    result = (f"💰 Загальні витрати: {total} грн\n"
              f"🍗 Їжа: {food} грн\n"
              f"🍾 Алкоголь: {alcohol} грн\n"
              f"🔥 Баня: {bath} грн")
    await message.answer(result)

async def main():
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
