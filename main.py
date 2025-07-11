from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
import os
import psycopg2

def conectar_banco():
    return psycopg2.connect(os.environ["DATABASE_URL"], sslmode='require')

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Fala jogador! ⚽🥇 Bem-vindo ao Telegram Bet! A Bet OFICIAL no telegram"
    )

async def acessar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    conn = conectar_banco()
    cur = conn.cursor()
    cur.execute("SELECT * FROM usuarios WHERE telegram_id = %s", (user.id,))
    result = cur.fetchone()

    if result:
        await update.message.reply_text(
            f"Acesso liberado com sucesso ✅\nNome: {user.first_name}\nID: {user.id}"
        )
    else:
        cur.execute(
            "INSERT INTO usuarios (telegram_id, nome) VALUES (%s, %s)",
            (user.id, user.first_name)
        )
        conn.commit()
        await update.message.reply_text(
            f"Acesso liberado com sucesso ✅\nNome: {user.first_name}\nID: {user.id}"
        )
    cur.close()
    conn.close()

if __name__ == '__main__':
    app = ApplicationBuilder().token(os.environ["BOT_TOKEN"]).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("acessar", acessar))
    print("✅ Bot iniciado com sucesso")
    app.run_polling()
              
