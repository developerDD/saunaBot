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
        [KeyboardButton(text="🧖‍♂️ Вибрати хто був у бані")],
        [KeyboardButton(text="💰 Додати витрати")],
        [KeyboardButton(text="🔥 Вказати вартість бані")],
        [KeyboardButton(text="🍾 Вказати хто пив алкоголь")],
        [KeyboardButton(text="🚿 Почати розрахунок")]
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

@dp.message(BathSession.adding_user)
async def save_user(message: types.Message, state: FSMContext):
    users[message.text] = message.text
   
    await message.answer(f"✅ Користувач {message.text} доданий!", reply_markup=main_menu)
    await state.clear()

@dp.message(F.text == "🧖‍♂️ Вибрати хто був у бані")
async def select_bath_visitors(message: types.Message, state: FSMContext):
    global expenses, bath_cost, alcohol_drinkers
    
    # Очищення фінансових даних
    expenses = {}
    bath_cost = 0
    alcohol_drinkers = []
    
    if not users:
        await message.answer("⚠️ Спочатку додайте користувачів!")
        return
    
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text=name, callback_data=f"visitor_{name}")] for name in users] +
                        [[InlineKeyboardButton(text="✅ Готово", callback_data="finalize_visitors")]]
    )
    await message.answer("Виберіть, хто був у бані (всі фінансові дані очищені):", reply_markup=keyboard)
    await state.set_state(BathSession.selecting_visitors)

@dp.callback_query(F.data.startswith("visitor_"), BathSession.selecting_visitors)
async def toggle_bath_visitor(callback: types.CallbackQuery):
    user = callback.data.replace("visitor_", "")
    if user in bath_visitors:
        bath_visitors.remove(user)
    else:
        bath_visitors.append(user)
    await callback.answer(f"✅ {user} {'доданий' if user in bath_visitors else 'видалений'} зі списку відвідувачів бані.")

@dp.callback_query(F.data == "finalize_visitors", BathSession.selecting_visitors)
async def finalize_bath_visitors(callback: types.CallbackQuery, state: FSMContext):
    if not bath_visitors:
        await callback.message.answer("⚠️ Ви не вибрали жодного відвідувача!")
        return
    
    await callback.message.answer("✅ Список відвідувачів бані збережено! Всі витрати обнулені.", reply_markup=main_menu)
    await state.clear()

@dp.message(F.text == "💰 Додати витрати")
async def add_expense_menu(message: types.Message, state: FSMContext):
    if not bath_visitors:
        await message.answer("⚠️ Спочатку потрібно вибрати, хто був у бані!")
        return
    
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text=name, callback_data=f"expense_{name}")] for name in bath_visitors]
    )
    await message.answer("Виберіть, хто зробив витрати:", reply_markup=keyboard)
    await state.set_state(BathSession.selecting_expense_user)

@dp.callback_query(F.data.startswith("expense_"), BathSession.selecting_expense_user)
async def select_expense_type(callback: types.CallbackQuery, state: FSMContext):
    user = callback.data.replace("expense_", "")
    await state.update_data(expense_user=user)
    
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🍗 Їжа", callback_data="expense_food")],
            [InlineKeyboardButton(text="🍾 Алкоголь", callback_data="expense_alcohol")]
        ]
    )
    await callback.message.answer(f"Виберіть тип витрат для {user}:", reply_markup=keyboard)
    await state.set_state(BathSession.selecting_expense_type)

@dp.callback_query(F.data.startswith("expense_"), BathSession.selecting_expense_type)
async def enter_expense_amount(callback: types.CallbackQuery, state: FSMContext):
    expense_type = callback.data.replace("expense_", "")
    await state.update_data(expense_type=expense_type)
    
    await callback.message.answer("Введіть суму витрат (тільки число):")
    await state.set_state(BathSession.entering_expense_amount)

@dp.message(BathSession.entering_expense_amount, F.text.regexp(r'\d+'))
async def save_expense(message: types.Message, state: FSMContext):
    data = await state.get_data()
    user = data.get("expense_user")
    expense_type = data.get("expense_type")
    amount = int(message.text)
    
    if user not in expenses:
        expenses[user] = {"food": 0, "alcohol": 0}
    
    expenses[user][expense_type] += amount
    
    await message.answer(f"✅ Витрати для {user} записані: {amount} грн на {('🍗 Їжа' if expense_type == 'food' else '🍾 Алкоголь')}", reply_markup=main_menu)
    await state.clear()




@dp.message(F.text == "🔥 Вказати вартість бані")
async def set_bath_cost(message: types.Message, state: FSMContext):
    await message.answer("Введіть загальну вартість бані (тільки число):")
    await state.set_state(BathSession.entering_bath_cost)

@dp.message(BathSession.entering_bath_cost, F.text.regexp(r'\d+'))
async def save_bath_cost(message: types.Message, state: FSMContext):
    global bath_cost
    bath_cost = int(message.text)
    await message.answer(f"✅ Вартість бані встановлена: {bath_cost} грн", reply_markup=main_menu)
    await state.clear()




@dp.message(F.text == "🍾 Вказати хто пив алкоголь")
async def select_alcohol_drinkers(message: types.Message, state: FSMContext):
    if not bath_visitors:
        await message.answer("⚠️ Спочатку потрібно вибрати, хто був у бані!")
        return
    
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text=name, callback_data=f"alcohol_{name}")] for name in bath_visitors] +
                        [[InlineKeyboardButton(text="✅ Готово", callback_data="finalize_alcohol")]]
    )
    await message.answer("Виберіть, хто вживав алкоголь:", reply_markup=keyboard)
    await state.set_state(BathSession.selecting_alcohol_drinkers)

@dp.callback_query(F.data.startswith("alcohol_"), BathSession.selecting_alcohol_drinkers)
async def toggle_alcohol_drinker(callback: types.CallbackQuery):
    user = callback.data.replace("alcohol_", "")
    if user in alcohol_drinkers:
        alcohol_drinkers.remove(user)
    else:
        alcohol_drinkers.append(user)
    await callback.answer(f"✅ {user} {'доданий' if user in alcohol_drinkers else 'видалений'} зі списку тих, хто пив алкоголь.")

@dp.callback_query(F.data == "finalize_alcohol", BathSession.selecting_alcohol_drinkers)
async def finalize_alcohol_selection(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.answer("✅ Список тих, хто пив алкоголь, збережено!", reply_markup=main_menu)
    await state.clear()
    

@dp.message(F.text == "🚿 Почати розрахунок")
async def finalize_calculation(message: types.Message):
    if not bath_visitors:
        await message.answer("⚠️ Спочатку потрібно вибрати, хто був у бані!")
        return
    if bath_cost == 0:
        await message.answer("⚠️ Вкажіть вартість бані перед розрахунком!")
        return
    
    total_food = sum(expenses[user].get("food", 0) for user in bath_visitors if user in expenses)
    total_alcohol = sum(expenses[user].get("alcohol", 0) for user in alcohol_drinkers if user in expenses)
    per_person_bath = bath_cost / len(bath_visitors) if bath_visitors else 0
    per_person_food = total_food / len(bath_visitors) if bath_visitors else 0
    per_person_alcohol = total_alcohol / len(alcohol_drinkers) if alcohol_drinkers else 0
    total_spent = total_food + total_alcohol + bath_cost
    
    result = "💰 **Підсумок витрат:**\n"
    result += f"🔹 Загальні витрати: {total_spent} грн\n"
    result += f"🍗 Їжа: {total_food} грн\n"
    result += f"🍾 Алкоголь: {total_alcohol} грн\n"
    result += f"🔥 Баня: {bath_cost} грн\n\n"
    
    for user in bath_visitors:
        paid = sum(expenses.get(user, {}).values())  # Якщо користувач відсутній – сума 0
        owes = per_person_bath + per_person_food - paid
        if user in alcohol_drinkers:
            owes += per_person_alcohol
        food_spent = expenses.get(user, {}).get("food", 0)
        alcohol_spent = expenses.get(user, {}).get("alcohol", 0)
        result += (f"👤 {user}: Витратив {paid} грн (🍗 {food_spent} грн, 🍾 {alcohol_spent} грн). "
                   f"Має сплатити: {owes:+.2f} грн\n")
    
    await message.answer(result, reply_markup=main_menu)

async def main():
    logging.info("✅ Бот запущено на Railway")
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.error("❌ Бот зупинено")
