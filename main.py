from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, MessageHandler, ContextTypes
from telegram.ext import filters
import csv
import datetime
import os

# Initialize data storage
USERS = {}


# Helper functions
def save_to_csv(user_id):
    if user_id in USERS:
        transactions = USERS[user_id].get("transactions", [])
        file_path = f"transactions_{user_id}.csv"
        with open(file_path, "w", newline="", encoding="utf-8") as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(["Date", "Type", "Category", "Amount"])
            for t in transactions:
                writer.writerow([t["date"], t["type"], t["category"], t["amount"]])
        return file_path
    return None


def get_monthly_report(user_id):
    if user_id not in USERS or "transactions" not in USERS[user_id]:
        return "ℹ️ *Нет данных для отчета.*"

    now = datetime.datetime.now()
    transactions = USERS[user_id]["transactions"]
    monthly_transactions = [t for t in transactions if t["date"].month == now.month and t["date"].year == now.year]

    income = sum(t["amount"] for t in monthly_transactions if t["type"] == "доход")
    expense = sum(t["amount"] for t in monthly_transactions if t["type"] == "расход")
    balance = income - expense

    report = f"📅 *Отчет за {now.strftime('%B %Y')}*\n"
    report += f"💰 Доход: *{income}*\n"
    report += f"💸 Расход: *{expense}*\n"
    report += f"📊 Баланс: *{balance}*"
    return report


# Command handlers
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in USERS:
        USERS[user_id] = {"transactions": [], "limit": None}
    await update.message.reply_text(
        "👋 Добро пожаловать в финансового бота!\nВведите /help для списка команд.\nЭтот бот поможет вам управлять вашими 💰 доходами и 💸 расходами.",
        parse_mode="Markdown"
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "*Список команд:*\n"
        "🔹 /add - Добавить транзакцию\n"
        "🔹 /edit - Изменить транзакцию\n"
        "🔹 /delete - Удалить транзакцию\n"
        "🔹 /transactions - Показать все транзакции\n"
        "🔹 /report - Показать отчет за месяц\n"
        "🔹 /setlimit - Установить лимит расходов\n"
        "🔹 /export - Экспортировать транзакции в CSV",
        parse_mode="Markdown"
    )


async def add_transaction(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not context.args:
        await update.message.reply_text(
            "⚠️ Для добавления транзакции используйте формат: *\n/add доход/расход, категория, сумма*\nПример: /add доход, зарплата, 5000",
            parse_mode="Markdown"
        )
        return

    try:
        data = " ".join(context.args).split(",")
        t_type, category, amount = data[0].strip(), data[1].strip(), float(data[2].strip())

        if t_type == "расход" and USERS[user_id].get("limit") is not None:
            total_expense = sum(t["amount"] for t in USERS[user_id]["transactions"] if t["type"] == "расход") + amount
            if total_expense > USERS[user_id]["limit"]:
                await update.message.reply_text("❌ Ошибка! Расход превышает установленный лимит.")
                return

        transaction = {"type": t_type, "category": category, "amount": amount, "date": datetime.datetime.now()}
        USERS[user_id]["transactions"].append(transaction)
        await update.message.reply_text("✅ Транзакция успешно добавлена!")
    except Exception:
        await update.message.reply_text("❌ Ошибка! Формат: /add доход/расход, категория, сумма")


async def edit_transaction(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in USERS or not USERS[user_id]["transactions"]:
        await update.message.reply_text("ℹ️ Нет транзакций для редактирования.")
        return


    if not context.args:
        await update.message.reply_text(
            "⚠️ Для редактирования транзакции используйте формат:\n"
            "/edit <индекс>, <доход/расход>, <категория>, <сумма>\n"
            "Пример: /edit 1, доход, премия, 2000",
            parse_mode="Markdown"
        )
        return

    try:
        data = " ".join(context.args).split(",")
        index = int(data[0].strip()) - 1  # Преобразование индекса в базу 0
        t_type, category, amount = data[1].strip(), data[2].strip(), float(data[3].strip())

        if 0 <= index < len(USERS[user_id]["transactions"]):
            USERS[user_id]["transactions"][index].update({
                "type": t_type,
                "category": category,
                "amount": amount,
                "date": datetime.datetime.now(),
            })
            await update.message.reply_text("✅ Транзакция успешно обновлена!")
        else:
            await update.message.reply_text("❌ Ошибка: указан неверный индекс.")
    except Exception:
        await update.message.reply_text(
            "❌ Ошибка! Формат: /edit <индекс>, <доход/расход>, <категория>, <сумма>",
            parse_mode="Markdown"
        )


async def delete_transaction(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in USERS or not USERS[user_id]["transactions"]:
        await update.message.reply_text("ℹ️ Нет транзакций для удаления.")
        return

    if not context.args:
        await update.message.reply_text(
            "⚠️ Для удаления транзакции используйте формат: *\n/delete <индекс>*\nПример: /delete 1",
            parse_mode="Markdown"
        )
        return

    try:
        index = int(context.args[0]) - 1  # Преобразование индекса в базу 0

        if 0 <= index < len(USERS[user_id]["transactions"]):
            USERS[user_id]["transactions"].pop(index)
            await update.message.reply_text("✅ Транзакция успешно удалена!")
        else:
            await update.message.reply_text("❌ Ошибка: указан неверный индекс.")
    except Exception:
        await update.message.reply_text("❌ Ошибка! Формат: /delete <индекс>")


async def transactions(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in USERS or not USERS[user_id]["transactions"]:
        await update.message.reply_text("ℹ️ Нет записанных транзакций.")
        return

    response = "📜 *Все транзакции:*\n"
    for i, t in enumerate(USERS[user_id]["transactions"], start=1):
        response += f"{i}. {t['date'].strftime('%Y-%m-%d')} - {t['type']} - {t['category']} - {t['amount']}\n"
    await update.message.reply_text(response, parse_mode="Markdown")


async def report(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    report_text = get_monthly_report(user_id)
    await update.message.reply_text(report_text, parse_mode="Markdown")


async def set_limit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not context.args:
        await update.message.reply_text(
            "⚠️ Для установки лимита используйте формат: *\n/setlimit сумма*\nПример: /setlimit 20000",
            parse_mode="Markdown"
        )
        return

    try:
        limit = float(context.args[0])
        USERS[user_id]["limit"] = limit
        await update.message.reply_text(f"✅ Лимит установлен: {limit}")
    except Exception:
        await update.message.reply_text("❌ Ошибка! Формат: /setlimit сумма")


async def export_transactions(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    file_path = save_to_csv(user_id)
    if file_path:
        with open(file_path, "rb") as f:
            await update.message.reply_document(f, filename=os.path.basename(file_path))
        os.remove(file_path)
    else:
        await update.message.reply_text("ℹ️ Нет данных для экспорта.")


# Main function
def main():
    application = ApplicationBuilder().token("7787143852:AAGvvBRNYjbVhL6KVJbPhTYCpZ3SI6s_Kdg").build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("add", add_transaction))
    application.add_handler(CommandHandler("edit", edit_transaction))
    application.add_handler(CommandHandler("delete", delete_transaction))
    application.add_handler(CommandHandler("transactions", transactions))
    application.add_handler(CommandHandler("report", report))
    application.add_handler(CommandHandler("setlimit", set_limit))
    application.add_handler(CommandHandler("export", export_transactions))

    application.run_polling()

if __name__ == "__main__":
    main()