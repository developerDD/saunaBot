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

# Список користувачів та їх витрати
users = {}
bath_visitors = []
alcohol_drinkers = []
expenses = {}
bath_cost = 0  # Вартість бані

class BathSession(StatesGroup):
    adding_user = State()
    selecting_visitors = State()
    selecting_alcohol_drinkers = State()
    selecting_expense_user = State()
    selecting_expense_type = State()
    entering_expense_amount = State()
    entering_bath_cost = State()
    confirming_expenses = State()

# Головне меню
main_menu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="➕ Додати користувача")],
        [KeyboardButton(text="💰 Додати витрати")],
        [KeyboardButton(text="🔥 Вказати вартість бані")],
        [KeyboardButton(text="🚿 Почати розрахунок")]
    ],
    resize_keyboard=True
)

@dp.message(Command("start"))
async def start(message: types.Message):
    await message.answer("Привіт! Я бот для розрахунку витрат на баню. Вибери дію:", reply_markup=main_menu)

@dp.message(F.text == "🔥 Вказати вартість бані")
async def set_bath_cost(message: types.Message, state: FSMContext):
    await message.answer("Введіть загальну вартість бані (тільки число):")
    await state.set_state(BathSession.entering_bath_cost)

@dp.message(F.text.regexp(r'\d+'), BathSession.entering_bath_cost)
async def save_bath_cost(message: types.Message, state: FSMContext):
    global bath_cost
    bath_cost = int(message.text)
    await message.answer(f"✅ Вартість бані встановлена: {bath_cost} грн", reply_markup=main_menu)
    await state.clear()

@dp.message(F.text == "🚿 Почати розрахунок")
async def start_calculation(message: types.Message, state: FSMContext):
    if not users:
        await message.answer("⚠️ Немає зареєстрованих користувачів!")
        return
    
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text=name, callback_data=f"visitor_{name}")] for name in users] +
                        [[InlineKeyboardButton(text="✅ Далі", callback_data="next")]]
    )
    await message.answer("Виберіть, хто був у бані:", reply_markup=keyboard)
    await state.set_state(BathSession.selecting_visitors)

@dp.callback_query(F.data == "next", BathSession.selecting_visitors)
async def select_alcohol_drinkers(callback: types.CallbackQuery, state: FSMContext):
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text=name, callback_data=f"drinker_{name}")] for name in bath_visitors] +
                        [[InlineKeyboardButton(text="✅ Далі", callback_data="finalize")]]
    )
    await callback.message.answer("Виберіть, хто пив алкоголь:", reply_markup=keyboard)
    await state.set_state(BathSession.selecting_alcohol_drinkers)

@dp.callback_query(F.data == "finalize", BathSession.selecting_alcohol_drinkers)
async def finalize_calculation(callback: types.CallbackQuery, state: FSMContext):
    global bath_cost
    total_food = sum(expenses[user]['food'] for user in bath_visitors)
    total_alcohol = sum(expenses[user]['alcohol'] for user in alcohol_drinkers)
    per_person_bath = bath_cost / len(bath_visitors) if bath_visitors else 0
    per_person_alcohol = total_alcohol / len(alcohol_drinkers) if alcohol_drinkers else 0
    per_person_food = total_food / len(bath_visitors) if bath_visitors else 0
    total_spent = total_food + total_alcohol + bath_cost
    
    result = "💰 **Підсумок витрат:**\n"
    result += f"🔹 Загальні витрати: {total_spent} грн\n"
    result += f"🍗 Їжа: {total_food} грн\n"
    result += f"🍾 Алкоголь: {total_alcohol} грн\n"
    result += f"🔥 Баня: {bath_cost} грн\n\n"
    
    for user in bath_visitors:
        paid = sum(expenses[user].values())
        owes = per_person_bath + per_person_food - paid
        if user in alcohol_drinkers:
            owes += per_person_alcohol
        result += f"👤 {user} витратив {paid} грн, має сплатити: {owes:+.2f} грн\n"
    
    await callback.message.answer(result, reply_markup=main_menu)
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
