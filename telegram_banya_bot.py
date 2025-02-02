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
expenses = {}

class BathSession(StatesGroup):
    adding_user = State()
    selecting_visitors = State()
    selecting_expense_user = State()
    selecting_expense_type = State()
    entering_expense_amount = State()
    confirming_expenses = State()

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
    await state.set_state(BathSession.adding_user)

@dp.message(F.text, BathSession.adding_user)
async def save_user(message: types.Message, state: FSMContext):
    user_name = message.text.strip()
    if user_name in users:
        await message.answer("⚠️ Такий користувач вже є!")
    else:
        users[user_name] = 0
        expenses[user_name] = {"food": 0, "alcohol": 0, "bath": 0}
        await message.answer(f"✅ Користувач {user_name} доданий!", reply_markup=main_menu)
    await state.clear()

@dp.message(F.text == "💰 Додати витрати")
async def add_expense_menu(message: types.Message, state: FSMContext):
    if not users:
        await message.answer("⚠️ Немає зареєстрованих користувачів!")
        return
    
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text=name, callback_data=f"expense_{name}")] for name in users]
    )
    await message.answer("Виберіть, хто зробив витрати:", reply_markup=keyboard)
    await state.set_state(BathSession.selecting_expense_user)

@dp.callback_query(F.data.startswith("expense_"), BathSession.selecting_expense_user)
async def select_expense_user(callback: types.CallbackQuery, state: FSMContext):
    selected_user = callback.data.replace("expense_", "")
    await state.update_data(expense_user=selected_user)
    
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🍗 Їжа")],
            [KeyboardButton(text="🍾 Алкоголь")],
            [KeyboardButton(text="🔥 Баня")]
        ],
        resize_keyboard=True
    )
    await callback.message.answer(f"Виберіть категорію витрат для {selected_user}:", reply_markup=keyboard)
    await state.set_state(BathSession.selecting_expense_type)

@dp.message(F.text.in_(["🍗 Їжа", "🍾 Алкоголь", "🔥 Баня"]), BathSession.selecting_expense_type)
async def ask_expense_amount(message: types.Message, state: FSMContext):
    category_map = {"🍗 Їжа": "food", "🍾 Алкоголь": "alcohol", "🔥 Баня": "bath"}
    category = category_map[message.text]
    await state.update_data(expense_category=category)
    await message.answer(f"Введіть суму витрат на {message.text} (тільки число):")
    await state.set_state(BathSession.entering_expense_amount)

@dp.message(F.text.regexp(r'\d+'), BathSession.entering_expense_amount)
async def save_expense(message: types.Message, state: FSMContext):
    data = await state.get_data()
    user = data["expense_user"]
    category = data["expense_category"]
    expenses[user][category] += int(message.text)
    await message.answer(f"✅ Витрати на {category} для {user} збережені!", reply_markup=main_menu)
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
async def finalize_calculation(callback: types.CallbackQuery, state: FSMContext):
    total_costs = {user: sum(expenses[user].values()) for user in bath_visitors}
    per_person = {user: total_costs[user] / len(bath_visitors) for user in bath_visitors}
    
    result = "💰 **Підсумок витрат:**\n"
    for user, total in total_costs.items():
        result += f"👤 {user}: {total} грн (має заплатити {per_person[user]:.2f} грн)\n"
    
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
