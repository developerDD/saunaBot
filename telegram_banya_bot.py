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
    entering_food_expense = State()
    entering_alcohol_expense = State()
    entering_bath_cost = State()

# Головне меню
main_menu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="➕ Додати користувача")],
        [KeyboardButton(text="🚿 Почати розрахунок")]
    ],
    resize_keyboard=True
)

@dp.message(Command("start"))
async def start(message: types.Message):
    await message.answer("Привіт! Я бот для розрахунку витрат на баню. Вибери дію:", reply_markup=main_menu)

@dp.message(lambda message: message.text == "➕ Додати користувача")
async def add_user(message: types.Message, state: FSMContext):
    await message.answer("Введіть ім'я користувача:")
    await state.set_state("adding_user")

@dp.message(F.text, state="adding_user")
async def save_user(message: types.Message, state: FSMContext):
    users[message.text] = 0
    await message.answer(f"✅ Користувач {message.text} доданий!", reply_markup=main_menu)
    await state.clear()

@dp.message(lambda message: message.text == "🚿 Почати розрахунок")
async def start_calculation(message: types.Message, state: FSMContext):
    if not users:
        await message.answer("⚠️ Немає зареєстрованих користувачів!")
        return
    
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text=name, callback_data=f"visitor_{name}")] for name in users]
    )
    await message.answer("Виберіть, хто був у бані:", reply_markup=keyboard)
    await state.set_state(BathSession.selecting_visitors)

@dp.callback_query(F.data.startswith("visitor_"), state=BathSession.selecting_visitors)
async def select_visitor(callback: types.CallbackQuery, state: FSMContext):
    visitor_name = callback.data.replace("visitor_", "")
    if visitor_name in bath_visitors:
        bath_visitors.remove(visitor_name)
    else:
        bath_visitors.append(visitor_name)
    
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text=name + (" ✅" if name in bath_visitors else ""), callback_data=f"visitor_{name}")] for name in users]
    )
    await callback.message.edit_text("Виберіть, хто був у бані:", reply_markup=keyboard)

@dp.message(F.text == "Далі", state=BathSession.selecting_visitors)
async def ask_food_expense(message: types.Message, state: FSMContext):
    await message.answer("Введіть витрати на їжу (тільки число):")
    await state.set_state(BathSession.entering_food_expense)

@dp.message(F.text.regexp(r'\d+'), state=BathSession.entering_food_expense)
async def save_food_expense(message: types.Message, state: FSMContext):
    expenses["food"] = int(message.text)
    await message.answer("Введіть витрати на алкоголь (тільки число):")
    await state.set_state(BathSession.entering_alcohol_expense)

@dp.message(F.text.regexp(r'\d+'), state=BathSession.entering_alcohol_expense)
async def save_alcohol_expense(message: types.Message, state: FSMContext):
    expenses["alcohol"] = int(message.text)
    await message.answer("Введіть загальну вартість бані (тільки число):")
    await state.set_state(BathSession.entering_bath_cost)

@dp.message(F.text.regexp(r'\d+'), state=BathSession.entering_bath_cost)
async def finalize_calculation(message: types.Message, state: FSMContext):
    expenses["bath"] = int(message.text)
    total_cost = sum(expenses.values())
    per_person = total_cost / len(bath_visitors)
    
    result = (f"💰 Загальні витрати: {total_cost} грн\n"
              f"🍗 Їжа: {expenses['food']} грн\n"
              f"🍾 Алкоголь: {expenses['alcohol']} грн\n"
              f"🔥 Баня: {expenses['bath']} грн\n"
              f"💳 Кожен відвідувач має заплатити: {per_person:.2f} грн")
    
    await message.answer(result, reply_markup=main_menu)
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
