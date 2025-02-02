import logging
import asyncio
import os
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext

# Отримуємо API-токен з змінних середовища
API_TOKEN = os.getenv("TELEGRAM_API_TOKEN")
if not API_TOKEN:
    raise ValueError("❌ TELEGRAM_API_TOKEN не встановлений! Додайте його у змінні середовища.")

# Логування
logging.basicConfig(level=logging.INFO)

# Ініціалізація бота та диспетчера
bot = Bot(token=API_TOKEN)
dp = Dispatcher()

# Список користувачів, які відвідують баню
users = {}
bath_visitors = []
expenses = {}

class BathSession(StatesGroup):
    selecting_visitors = State()
    selecting_expense_type = State()
    entering_food_expense = State()
    entering_alcohol_expense = State()
    entering_bath_cost = State()

# Головне меню
main_menu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="➕ Додати користувача")],
        [KeyboardButton(text="🚿 Почати розрахунок")],
        [KeyboardButton(text="💰 Додати витрати")]
    ],
    resize_keyboard=True
)

@dp.message(Command("start"))
async def start(message: types.Message):
    await message.answer("Привіт! Я бот для розрахунку витрат на баню. Вибери дію:", reply_markup=main_menu)

@dp.message(F.text == "➕ Додати користувача")
async def add_user(message: types.Message, state: FSMContext):
    await message.answer("Введіть ім'я користувача:")
    await state.set_state(BathSession.selecting_visitors)

@dp.message(F.text == "💰 Додати витрати")
async def add_expense_menu(message: types.Message, state: FSMContext):
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🍗 Додати витрати на їжу")],
            [KeyboardButton(text="🍾 Додати витрати на алкоголь")],
            [KeyboardButton(text="🔥 Додати вартість бані")],
            [KeyboardButton(text="🔙 Назад")]
        ],
        resize_keyboard=True
    )
    await message.answer("Оберіть категорію витрат:", reply_markup=keyboard)
    await state.set_state(BathSession.selecting_expense_type)

@dp.message(F.text == "🍗 Додати витрати на їжу", state=BathSession.selecting_expense_type)
async def ask_food_expense(message: types.Message, state: FSMContext):
    await message.answer("Введіть витрати на їжу (тільки число):")
    await state.set_state(BathSession.entering_food_expense)

@dp.message(F.text == "🍾 Додати витрати на алкоголь", state=BathSession.selecting_expense_type)
async def ask_alcohol_expense(message: types.Message, state: FSMContext):
    await message.answer("Введіть витрати на алкоголь (тільки число):")
    await state.set_state(BathSession.entering_alcohol_expense)

@dp.message(F.text == "🔥 Додати вартість бані", state=BathSession.selecting_expense_type)
async def ask_bath_cost(message: types.Message, state: FSMContext):
    await message.answer("Введіть загальну вартість бані (тільки число):")
    await state.set_state(BathSession.entering_bath_cost)

@dp.message(F.text.regexp(r'\d+'), state=BathSession.entering_food_expense)
async def save_food_expense(message: types.Message, state: FSMContext):
    expenses["food"] = int(message.text)
    await message.answer("✅ Витрати на їжу збережені!", reply_markup=main_menu)
    await state.clear()

@dp.message(F.text.regexp(r'\d+'), state=BathSession.entering_alcohol_expense)
async def save_alcohol_expense(message: types.Message, state: FSMContext):
    expenses["alcohol"] = int(message.text)
    await message.answer("✅ Витрати на алкоголь збережені!", reply_markup=main_menu)
    await state.clear()

@dp.message(F.text.regexp(r'\d+'), state=BathSession.entering_bath_cost)
async def save_bath_cost(message: types.Message, state: FSMContext):
    expenses["bath"] = int(message.text)
    await message.answer("✅ Вартість бані збережена!", reply_markup=main_menu)
    await state.clear()

async def main():
    logging.info("✅ Бот запущено на Railway")
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.error("❌ Бот зупинено")
