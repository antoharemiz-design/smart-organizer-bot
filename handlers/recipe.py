from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from services.ai import get_recipe
from database.db import add_favorite, get_favorites, remove_favorite
import json

router = Router()

# ----- Главное меню (обычные кнопки) -----
main_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="🍳 Придумать рецепт")],
        [KeyboardButton(text="⭐ Мои избранные")],
        [KeyboardButton(text="⚙️ Профиль"), KeyboardButton(text="❓ Помощь")]
    ],
    resize_keyboard=True,
    input_field_placeholder="Выберите действие"
)

# ----- Вспомогательные клавиатуры -----
back_kb = ReplyKeyboardMarkup(
    keyboard=[[KeyboardButton(text="🔙 Главное меню")]],
    resize_keyboard=True
)

# ----- Команда /start -----
@router.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer(
        "👋 Привет! Я твой личный шеф-помощник.\n"
        "Выбери действие в меню или просто напиши список продуктов.\n\n"
        "Если хочешь, чтобы я учёл твои предпочтения (диета, аллергии), "
        "заполни профиль в разделе ⚙️ Профиль.",
        reply_markup=main_kb
    )

# ----- Возврат в главное меню -----
@router.message(F.text == "🔙 Главное меню")
async def back_to_main(message: types.Message):
    await message.answer("Главное меню", reply_markup=main_kb)

# ----- Кнопка "Придумать рецепт" -----
@router.message(F.text == "🍳 Придумать рецепт")
async def prompt_products(message: types.Message):
    await message.answer(
        "Напиши список продуктов через запятую.\n"
        "Например: <i>курица, лук, сметана, гречка</i>\n\n"
        "Или можешь просто сказать: «хочу итальянский ужин»",
        parse_mode="HTML"
    )

# ----- Кнопка "Мои избранные" -----
@router.message(F.text == "⭐ Мои избранные")
async def show_favorites(message: types.Message):
    favs = await get_favorites(message.from_user.id)
    if not favs:
        await message.answer("У вас пока нет избранных рецептов.", reply_markup=main_kb)
        return

    # Показываем список названий с кнопками для просмотра и удаления
    builder = InlineKeyboardBuilder()
    for i, rec in enumerate(favs):
        title = rec.get('title', f'Рецепт {i+1}')
        # Обрезаем длинные названия
        short_title = title[:30] + '…' if len(title) > 30 else title
        builder.row(InlineKeyboardButton(
            text=short_title,
            callback_data=f"view_fav:{i}"
        ))
    builder.adjust(1)
    await message.answer(
        "⭐ Ваши избранные рецепты (нажмите для деталей):",
        reply_markup=builder.as_markup()
    )

# ----- Обработчик инлайн-кнопок (просмотр/удаление из избранного) -----
@router.callback_query(F.data.startswith("view_fav:"))
async def view_favorite(callback: types.CallbackQuery):
    index = int(callback.data.split(":")[1])
    favs = await get_favorites(callback.from_user.id)
    if index >= len(favs):
        await callback.answer("Рецепт не найден.", show_alert=True)
        return

    recipe = favs[index]
    text = format_recipe(recipe)
    # Кнопка удаления
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(
        text="🗑 Удалить из избранного",
        callback_data=f"del_fav:{index}"
    ))
    await callback.message.answer(text, parse_mode="HTML", reply_markup=builder.as_markup())
    await callback.answer()

@router.callback_query(F.data.startswith("del_fav:"))
async def delete_favorite(callback: types.CallbackQuery):
    index = int(callback.data.split(":")[1])
    favs = await get_favorites(callback.from_user.id)
    if index >= len(favs):
        await callback.answer("Рецепт уже удалён.", show_alert=True)
        return
    title = favs[index].get('title', '')
    success = await remove_favorite(callback.from_user.id, title)
    if success:
        await callback.answer("Удалено!", show_alert=True)
        await callback.message.delete()
    else:
        await callback.answer("Ошибка удаления.", show_alert=True)

# ----- Обработка ввода продуктов или пожеланий -----
@router.message(lambda msg: msg.text and not msg.text.startswith('/') and msg.text not in [
    "🍳 Придумать рецепт", "⭐ Мои избранные", "⚙️ Профиль", "❓ Помощь", "🔙 Главное меню"
])
async def generate_recipe(message: types.Message):
    user_input = message.text.strip()
    if len(user_input) < 3:
        await message.answer("Пожалуйста, напиши хотя бы пару продуктов или запрос.")
        return

    # Загружаем предпочтения пользователя (если есть)
    from database.db import DB_PATH
    import aiosqlite
    prefs = {}
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT diet, allergies, dislikes FROM user_prefs WHERE user_id = ?", (message.from_user.id,))
        row = await cursor.fetchone()
        if row:
            prefs['diet'] = row[0]
            prefs['allergies'] = row[1]
            prefs['dislikes'] = row[2]

    # Собираем промпт с учётом предпочтений
    extra = ""
    if prefs.get('diet'):
        extra += f"Диета: {prefs['diet']}. "
    if prefs.get('allergies'):
        extra += f"Аллергии: {prefs['allergies']}. "
    if prefs.get('dislikes'):
        extra += f"Не любит: {prefs['dislikes']}. "
    if extra:
        extra = "Учти предпочтения: " + extra

    await message.answer("Готовлю рецепт...")
    recipe = await get_recipe(user_input, extra_context=extra)  # обновим функцию ai.py

    if recipe is None:
        await message.answer("Не удалось создать рецепт. Попробуй другой запрос.")
        return

    # Форматируем и показываем рецепт
    response_text = format_recipe(recipe)

    # Inline-кнопка "Добавить в избранное"
    builder = InlineKeyboardBuilder()
    # Передаём рецепт как JSON в callback_data (с ограничением по длине)
    recipe_json = json.dumps(recipe, ensure_ascii=False)
    if len(recipe_json) > 3000:  # Telegram ограничение на callback_data 64 байта, но можно использовать cache или сократить
        # Вместо этого сохраняем рецепт во временный словарь (в памяти) или используем короткий идентификатор
        # Пока для простоты сделаем кнопку без данных, сохраняя через кэш (но лучше через БД сразу)
        # Для MVP просто добавим кнопку, которая вызовет сохранение через сообщение
        await message.answer(response_text, parse_mode="HTML")
        await message.answer("Хотите сохранить рецепт в избранное? Нажмите /save", reply_markup=back_kb)
    else:
        builder.row(InlineKeyboardButton(
            text="⭐ В избранное",
            callback_data=f"save_fav:{recipe_json}"
        ))
        await message.answer(response_text, parse_mode="HTML", reply_markup=builder.as_markup())

# ----- Обработчик сохранения в избранное (inline) -----
@router.callback_query(F.data.startswith("save_fav:"))
async def save_to_favorites(callback: types.CallbackQuery):
    recipe_json = callback.data.split(":", 1)[1]
    try:
        recipe = json.loads(recipe_json)
    except:
        await callback.answer("Ошибка сохранения.", show_alert=True)
        return
    await add_favorite(callback.from_user.id, recipe)
    await callback.answer("Добавлено в избранное! ⭐", show_alert=True)
    # Можно изменить кнопку или просто убрать
    await callback.message.edit_reply_markup(reply_markup=None)

# ----- Команда /save (если кнопка не влезла) -----
@router.message(Command("save"))
async def cmd_save(message: types.Message):
    # Просим пользователя ответить на сообщение с рецептом, которое нужно сохранить
    await message.answer("Ответьте на сообщение с рецептом, который хотите сохранить, командой /save")

# ----- Кнопка "Помощь" -----
@router.message(F.text == "❓ Помощь")
async def help_cmd(message: types.Message):
    await message.answer(
        "Я могу:\n"
        "• Придумать рецепт из твоих продуктов\n"
        "• Учесть диету и аллергии (заполни ⚙️ Профиль)\n"
        "• Сохранить рецепт в избранное\n\n"
        "Просто нажми на кнопку или напиши запрос!",
        reply_markup=main_kb
    )

# ----- Заглушка для профиля (позже сделаем полноценный) -----
@router.message(F.text == "⚙️ Профиль")
async def profile_menu(message: types.Message):
    await message.answer(
        "Здесь можно настроить твои предпочтения.\n"
        "Пока эта функция в разработке. Хочешь помочь? Напиши /setprefs",
        reply_markup=main_kb
    )

# Вспомогательная функция форматирования рецепта
def format_recipe(recipe: dict) -> str:
    text = (
        f"🍽 <b>{recipe.get('title', 'Блюдо')}</b>\n"
        f"⏱ Время: {recipe.get('cooking_time', 'не указано')}\n"
        f"📊 Сложность: {recipe.get('difficulty', 'не указана')}\n\n"
        f"<b>Ингредиенты:</b>\n" + "\n".join(f"• {ing}" for ing in recipe.get('ingredients', [])) + "\n\n"
        f"<b>Приготовление:</b>\n" + "\n".join(f"{i+1}. {step}" for i, step in enumerate(recipe.get('steps', [])))
    )
    if recipe.get('tip'):
        text += f"\n\n💡 <i>Совет: {recipe['tip']}</i>"
    return text