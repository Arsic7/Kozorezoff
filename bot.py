import logging
import re

from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
    ConversationHandler
)

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

TIME, TASK, DELETE_TIME, EDIT_CHOICE, EDIT_TIME, EDIT_TASK = range(6)
user_tasks = {}


def get_main_keyboard():
    return ReplyKeyboardMarkup([
        ["Добавить задачу", "Удалить задачу"],
        ["Редактировать задачу", "Показать расписание"],
        ["Очистить всё", "Помощь"]
    ], resize_keyboard=True)


def is_valid_time(time_str):
    return bool(re.match(r"^([0-1]?[0-9]|2[0-3]):[0-5][0-9]$", time_str))


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "⏰ Бот-планировщик\nВыберите действие:",
        reply_markup=get_main_keyboard()
    )
    return ConversationHandler.END


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = (
        "📋 Справка:\n"
        "1. Добавить задачу - введите время и задачу\n"
        "2. Удалить задачу - введите время задачи\n"
        "3. Редактировать задачу - изменить существующую задачу\n"
        "4. Показать расписание - все текущие задачи\n"
        "5. Очистить всё - удалить все задачи\n"
        "Формат времени: ЧЧ:ММ (например 12:30)"
    )
    await update.message.reply_text(help_text)
    return ConversationHandler.END


async def add_task_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Введите время и задачу в формате: ЧЧ:ММ Задача\nНапример: 12:30 Обед")
    return TIME


async def add_task_time(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if not re.match(r"^([0-1]?[0-9]|2[0-3]):[0-5][0-9] .+", text):
        await update.message.reply_text(
            "Неверный формат. Введите время и задачу в формате: ЧЧ:ММ Задача\nНапример: 12:30 Обед")
        return TIME

    time, task = text.split(' ', 1)
    user_id = update.effective_user.id
    if user_id not in user_tasks:
        user_tasks[user_id] = {}
    user_tasks[user_id][time] = task
    await update.message.reply_text(f"✅ Добавлено: {time} - {task}", reply_markup=get_main_keyboard())
    return ConversationHandler.END


async def edit_task_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in user_tasks or not user_tasks[user_id]:
        await update.message.reply_text("Нет задач для редактирования", reply_markup=get_main_keyboard())
        return ConversationHandler.END
    tasks = "\n".join([f"{i + 1}. {time} - {task}" for i, (time, task) in enumerate(user_tasks[user_id].items())])
    await update.message.reply_text(f"Выберите задачу для редактирования:\n{tasks}\n\nВведите номер задачи:")
    return EDIT_CHOICE
async def edit_task_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    try:
        choice = int(update.message.text) - 1
        task_list = list(user_tasks[user_id].items())
        if 0 <= choice < len(task_list):
            context.user_data['edit_time'] = task_list[choice][0]
            await update.message.reply_text("Введите новое время (ЧЧ:ММ):")
            return EDIT_TIME
        else:
            await update.message.reply_text("Неверный номер задачи, попробуйте снова:")
            return EDIT_CHOICE
    except ValueError:
        await update.message.reply_text("Введите номер задачи цифрой:")
        return EDIT_CHOICE
async def edit_task_time(update: Update, context: ContextTypes.DEFAULT_TYPE):
    new_time = update.message.text
    if not is_valid_time(new_time):
        await update.message.reply_text("Неверный формат времени. Введите в формате ЧЧ:ММ:")
        return EDIT_TIME
    context.user_data['new_time'] = new_time
    await update.message.reply_text("Введите новое описание задачи:")
    return EDIT_TASK
async def edit_task_description(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    old_time = context.user_data['edit_time']
    new_time = context.user_data['new_time']
    new_task = update.message.text
    if old_time in user_tasks[user_id]:
        del user_tasks[user_id][old_time]
    user_tasks[user_id][new_time] = new_task
    await update.message.reply_text(f"✅ Задача обновлена: {new_time} - {new_task}", reply_markup=get_main_keyboard())
    return ConversationHandler.END


async def remove_task_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Введите время задачи для удаления в формате ЧЧ:ММ\nНапример: 12:30")
    return DELETE_TIME


async def remove_task_time(update: Update, context: ContextTypes.DEFAULT_TYPE):
    time = update.message.text
    user_id = update.effective_user.id
    if not is_valid_time(time):
        await update.message.reply_text("Неверный формат времени. Введите в формате ЧЧ:ММ\nНапример: 12:30")
        return DELETE_TIME
    if user_id in user_tasks and time in user_tasks[user_id]:
        del user_tasks[user_id][time]
        await update.message.reply_text(f"❌ Удалено: {time}", reply_markup=get_main_keyboard())
    else:
        await update.message.reply_text("⚠️ Задача не найдена!", reply_markup=get_main_keyboard())
    return ConversationHandler.END


async def view_schedule(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in user_tasks or not user_tasks[user_id]:
        await update.message.reply_text("📭 Расписание пусто!", reply_markup=get_main_keyboard())
        return ConversationHandler.END

    tasks = "\n".join([f"⏰ {time} - {task}" for time, task in sorted(user_tasks[user_id].items())])
    await update.message.reply_text(f"📅 Ваше расписание:\n{tasks}", reply_markup=get_main_keyboard())
    return ConversationHandler.END


async def clear_schedule(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id in user_tasks:
        user_tasks[user_id].clear()
    await update.message.reply_text("🧹 Расписание очищено!", reply_markup=get_main_keyboard())
    return ConversationHandler.END


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if text == "Добавить задачу":
        return await add_task_start(update, context)
    elif text == "Удалить задачу":
        return await remove_task_start(update, context)
    elif text == "Редактировать задачу":
        return await edit_task_start(update, context)
    elif text == "Показать расписание":
        return await view_schedule(update, context)
    elif text == "Очистить всё":
        return await clear_schedule(update, context)
    elif text == "Помощь":
        return await help_command(update, context)
    else:
        await update.message.reply_text("Используйте кнопки для управления", reply_markup=get_main_keyboard())
        return ConversationHandler.END


def main():
    application = Application.builder().token("8014681068:AAF1nDtwPnW9G-5Hpy6wRD3oa8AqOtJF-AU").build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))

    conv_handler_add = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("^Добавить задачу$"), add_task_start)],
        states={
            TIME: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_task_time)],
        },
        fallbacks=[]
    )

    conv_handler_edit = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("^Редактировать задачу$"), edit_task_start)],
        states={
            EDIT_CHOICE: [MessageHandler(filters.TEXT & ~filters.COMMAND, edit_task_choice)],
            EDIT_TIME: [MessageHandler(filters.TEXT & ~filters.COMMAND, edit_task_time)],
            EDIT_TASK: [MessageHandler(filters.TEXT & ~filters.COMMAND, edit_task_description)]
        },
        fallbacks=[]
    )

    conv_handler_remove = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("^Удалить задачу$"), remove_task_start)],
        states={
            DELETE_TIME: [MessageHandler(filters.TEXT & ~filters.COMMAND, remove_task_time)],
        },
        fallbacks=[]
    )

    application.add_handler(conv_handler_add)
    application.add_handler(conv_handler_edit)
    application.add_handler(conv_handler_remove)
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    application.run_polling()


if __name__ == "__main__":
    main()
