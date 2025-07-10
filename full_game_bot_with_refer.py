
import logging
import random
import sqlite3
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters

BOT_TOKEN = "7492803380:AAED9EvIzOJJ7NII84OJUmtHJ-HijA3kCQQ"
UPI_ID = "9341910565@ptyes"
ADMIN_USERNAME = "MANDAL4482"

# Database setup
conn = sqlite3.connect("users.db", check_same_thread=False)
cursor = conn.cursor()
cursor.execute("CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, balance INTEGER DEFAULT 0, referred_by INTEGER, has_played INTEGER DEFAULT 0)")
conn.commit()

def get_balance(user_id):
    cursor.execute("SELECT balance FROM users WHERE id=?", (user_id,))
    row = cursor.fetchone()
    if row:
        return row[0]
    else:
        cursor.execute("INSERT INTO users (id, balance) VALUES (?, ?)", (user_id, 0))
        conn.commit()
        return 0

def update_balance(user_id, amount):
    current = get_balance(user_id)
    new_balance = current + amount
    cursor.execute("UPDATE users SET balance=? WHERE id=?", (new_balance, user_id))
    conn.commit()
    return new_balance

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    if ' '.join(context.args):
        try:
            referrer_id = int(context.args[0])
            if referrer_id != user_id:
                cursor.execute("SELECT referred_by FROM users WHERE id=?", (user_id,))
                row = cursor.fetchone()
                if not row:
                    cursor.execute("INSERT INTO users (id, balance, referred_by) VALUES (?, ?, ?)", (user_id, 0, referrer_id))
                    conn.commit()
        except:
            pass

    await update.message.reply_text(
        "🎮 *Welcome to the Game Bot!*

"
        "Commands:
"
        "/deposit - पैसे जमा करें
"
        "/balance - बैलेंस चेक करें
"
        "/2xgame - 2X गेम (20% चांस)
"
        "/spin - Spin गेम
"
        "/withdraw - पैसा निकालें
"
        "/refer - रेफरल लिंक शेयर करें",
        parse_mode="Markdown"
    )

async def refer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.message.from_user.id
    await update.message.reply_text(
        f"🔗 अपना रेफरल लिंक:
https://t.me/{context.bot.username}?start={uid}

"
        "जैसे ही कोई इसमें जुड़ता है और गेम खेलता है, आपको ₹5 मिलेगा!"
    )

async def deposit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        f"💸 *Manual Deposit*
Pay ₹10 - ₹10000 to this UPI:
`{UPI_ID}`

"
        "🖼️ उसके बाद पेमेंट का स्क्रीनशॉट भेजें।",
        parse_mode="Markdown"
    )

async def handle_screenshot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    if update.message.photo:
        await update.message.forward(chat_id=update.effective_chat.id)
        await update.message.reply_text("✅ स्क्रीनशॉट भेजा गया। Admin द्वारा approve होने के बाद बैलेंस जुड़ जाएगा।")
    else:
        await update.message.reply_text("❌ कृपया स्क्रीनशॉट इमेज भेजें।")

async def balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    bal = get_balance(update.message.from_user.id)
    await update.message.reply_text(f"💰 आपका बैलेंस है: ₹{bal}")

async def twoxgame(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    cursor.execute("SELECT has_played FROM users WHERE id=?", (user_id,))
    first = cursor.fetchone()
    if first and first[0] == 0:
        cursor.execute("UPDATE users SET has_played=1 WHERE id=?", (user_id,))
        cursor.execute("SELECT referred_by FROM users WHERE id=?", (user_id,))
        ref = cursor.fetchone()
        if ref and ref[0]:
            update_balance(ref[0], 5)
    keyboard = [[InlineKeyboardButton(f"₹{amt}", callback_data=f"2x_{amt}") for amt in [1, 2, 5]],
                [InlineKeyboardButton(f"₹{amt}", callback_data=f"2x_{amt}") for amt in [10, 20, 50]]]
    await update.message.reply_text("💥 2X गेम:
बेट अमाउंट चुनें:", reply_markup=InlineKeyboardMarkup(keyboard))

async def spin_game(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[InlineKeyboardButton(f"₹{amt}", callback_data=f"spin_{amt}") for amt in [1, 2, 5]],
                [InlineKeyboardButton(f"₹{amt}", callback_data=f"spin_{amt}") for amt in [10, 20, 50]]]
    await update.message.reply_text("🎰 Spin गेम:
बेट अमाउंट चुनें:", reply_markup=InlineKeyboardMarkup(keyboard))

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    await query.answer()

    if query.data.startswith("2x_"):
        amount = int(query.data.split("_")[1])
        if get_balance(user_id) < amount:
            await query.edit_message_text("❌ पर्याप्त बैलेंस नहीं।")
            return
        result = random.randint(1, 100)
        if result <= 20:
            update_balance(user_id, amount)
            await query.edit_message_text(f"🎉 जीत गए! ₹{amount*2} मिला।")
        else:
            update_balance(user_id, -amount)
            await query.edit_message_text(f"😢 हार गए। ₹{amount} कट गया।")

    elif query.data.startswith("spin_"):
        amount = int(query.data.split("_")[1])
        if get_balance(user_id) < amount:
            await query.edit_message_text("❌ पर्याप्त बैलेंस नहीं।")
            return
        update_balance(user_id, -amount)
        prize = random.choices([0, 0.5, 1, 2], weights=[60, 25, 10, 5])[0]
        winnings = int(amount * prize)
        update_balance(user_id, winnings)
        await query.edit_message_text(f"🎰 Result: {prize}x
💵 ₹{winnings} मिला।")

async def withdraw(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🏦 *Withdrawal*
Format:
`withdraw 1000 AC123456789 IFSC0000`",
        parse_mode="Markdown"
    )

async def handle_withdraw(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message.text
    if msg.startswith("withdraw"):
        parts = msg.split()
        if len(parts) == 4:
            amt = int(parts[1])
            account = parts[2]
            ifsc = parts[3]
            uid = update.message.from_user.id
            if get_balance(uid) >= amt:
                update_balance(uid, -amt)
                await context.bot.send_message(update.effective_chat.id, f"📤 Withdrawal:
User: {uid}
Amt: ₹{amt}
A/C: {account}
IFSC: {ifsc}")
                await update.message.reply_text("✅ Withdrawal भेजा गया।")
            else:
                await update.message.reply_text("❌ बैलेंस कम है।")
        else:
            await update.message.reply_text("⚠️ Format ग़लत है।")

def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("deposit", deposit))
    app.add_handler(CommandHandler("balance", balance))
    app.add_handler(CommandHandler("2xgame", twoxgame))
    app.add_handler(CommandHandler("spin", spin_game))
    app.add_handler(CommandHandler("withdraw", withdraw))
    app.add_handler(CommandHandler("refer", refer))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_withdraw))
    app.add_handler(MessageHandler(filters.PHOTO, handle_screenshot))
    print("Bot running...")
    app.run_polling()

if __name__ == "__main__":
    main()
