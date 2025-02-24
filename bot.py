import telegram
from telegram.ext import Application, CommandHandler
import json
import os
from datetime import datetime

# Получаем токен из переменной окружения (для сервера)
TOKEN = os.getenv("TOKEN", "7522266813:AAFvvEylkfLgJavkSTRqHIXhqowMBIfywJk")

# Создаем приложение
print("Инициализация бота...")
try:
    application = Application.builder().token(TOKEN).build()
    print("Бот успешно инициализирован!")
except Exception as e:
    print(f"Ошибка при инициализации бота: {str(e)}")
    exit()

# Файл для хранения напоминаний
REMINDERS_FILE = "reminders.json"

# Загружаем существующие напоминания из файла
def load_reminders():
    if os.path.exists(REMINDERS_FILE):
        with open(REMINDERS_FILE, "r") as file:
            return json.load(file)
    return {"future": [], "past": []}

# Сохраняем напоминания в файл
def save_reminders(reminders):
    with open(REMINDERS_FILE, "w") as file:
        json.dump(reminders, file, ensure_ascii=False, indent=4)
    print(f"Сохранено в файл: {reminders}")

# Команда /start
async def start(update, context):
    print("Команда /start получена")
    await update.message.reply_text("Привет! Я бот для напоминаний. Используй:\n/remind <дата> <время> <текст>\n/list — показать задачи\n/clearpast — очистить прошедшие\n/delete <текст> или /delete all")

# Функция отправки напоминания
async def send_reminder(context):
    job = context.job
    chat_id = job.data["chat_id"]
    text = job.data["text"]
    await context.bot.send_message(chat_id=chat_id, text=f"Напоминание: {text}")
    print(f"Отправлено напоминание: {text}")

    # Переносим задачу в прошедшие
    reminders = load_reminders()
    for reminder in reminders["future"]:
        if reminder["chat_id"] == chat_id and reminder["text"] == text:
            reminders["past"].append(reminder)
            reminders["future"].remove(reminder)
            break
    save_reminders(reminders)

# Команда /remind
async def remind(update, context):
    print("Команда /remind получена")
    try:
        args = context.args
        if len(args) < 3:
            await update.message.reply_text("Напиши: /remind <дата> <время> <текст>\nПример: /remind 25.02.2025 14:00 Купить молоко")
            return
        
        date_str = args[0]
        time_str = args[1]
        reminder_text = " ".join(args[2:])

        remind_time = datetime.strptime(f"{date_str} {time_str}", "%d.%m.%Y %H:%M")
        current_time = datetime.now()
        
        if remind_time <= current_time:
            await update.message.reply_text("Ошибка: время напоминания уже прошло!")
            return
        
        reminders = load_reminders()
        new_reminder = {
            "time": remind_time.strftime("%d.%m.%Y %H:%M"),
            "text": reminder_text,
            "chat_id": update.message.chat_id
        }
        reminders["future"].append(new_reminder)
        save_reminders(reminders)
        
        # Планируем задачу через job_queue
        delay = (remind_time - current_time).total_seconds()
        if context.job_queue is None:
            raise ValueError("JobQueue не инициализирован!")
        context.job_queue.run_once(send_reminder, delay, data={"chat_id": update.message.chat_id, "text": reminder_text})
        
        print(f"Добавлено напоминание: {new_reminder}")
        await update.message.reply_text(f"Напоминание установлено: {reminder_text} на {date_str} {time_str}")
    except Exception as e:
        await update.message.reply_text(f"Ошибка: {str(e)}. Убедись, что формат правильный: /remind 25.02.2025 14:00 <текст>")
        print(f"Ошибка в /remind: {str(e)}")

# Команда /list
async def list_reminders(update, context):
    print("Команда /list получена")
    reminders = load_reminders()
    
    future_text = "Будущие задачи:\n"
    for r in reminders["future"]:
        future_text += f"{r['time']} — {r['text']}\n"
    
    past_text = "Прошедшие задачи:\n"
    for r in reminders["past"]:
        past_text += f"{r['time']} — {r['text']}\n"
    
    if not reminders["future"]:
        future_text += "Нет будущих задач.\n"
    if not reminders["past"]:
        past_text += "Нет прошедших задач.\n"
    
    await update.message.reply_text(f"{future_text}\n{past_text}")
    print(f"Список задач: future={reminders['future']}, past={reminders['past']}")

# Команда /clearpast
async def clear_past(update, context):
    print("Команда /clearpast получена")
    reminders = load_reminders()
    reminders["past"] = []
    save_reminders(reminders)
    await update.message.reply_text("Список прошедших задач очищен!")

# Команда /delete
async def delete(update, context):
    print("Команда /delete получена")
    try:
        args = context.args
        if not args:
            await update.message.reply_text("Напиши: /delete <текст задачи> или /delete all\nПример: /delete Купить молоко")
            return
        
        reminders = load_reminders()
        if args[0].lower() == "all":
            # Удаляем только будущие задачи
            reminders["future"] = []
            save_reminders(reminders)
            await update.message.reply_text("Все будущие задачи удалены!")
            return
        
        task_text = " ".join(args)
        for i, reminder in enumerate(reminders["future"]):
            if reminder["text"] == task_text and reminder["chat_id"] == update.message.chat_id:
                reminders["future"].pop(i)
                save_reminders(reminders)
                await update.message.reply_text(f"Задача '{task_text}' удалена!")
                return
        for i, reminder in enumerate(reminders["past"]):
            if reminder["text"] == task_text and reminder["chat_id"] == update.message.chat_id:
                reminders["past"].pop(i)
                save_reminders(reminders)
                await update.message.reply_text(f"Задача '{task_text}' удалена из прошедших!")
                return
        
        await update.message.reply_text(f"Задача '{task_text}' не найдена!")
    except Exception as e:
        await update.message.reply_text(f"Ошибка: {str(e)}")

# Регистрируем команды
print("Регистрирую команды...")
application.add_handler(CommandHandler("start", start))
application.add_handler(CommandHandler("remind", remind))
application.add_handler(CommandHandler("list", list_reminders))
application.add_handler(CommandHandler("clearpast", clear_past))
application.add_handler(CommandHandler("delete", delete))

# Запускаем бота
print("Бот запускается...")
try:
    application.run_polling()
    print("Polling запущен!")
except Exception as e:
    print(f"Ошибка при запуске polling: {str(e)}")