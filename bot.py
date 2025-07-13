import os
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
import sqlite3

# Função para conectar ao banco de dados
def conectar():
    return sqlite3.connect("apostas.db")

# Comando /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("✅ Acessar", callback_data="acessar")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        "Fala jogador! ⚽🥇 Bem-vindo ao Telegram Bet! A Bet OFICIAL no telegram",
        reply_markup=reply_markup
    )

# Comando /acessar (função principal de login)
async def acessar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    nome = update.effective_user.first_name
    id_telegram = update.effective_user.id

    # Conecta e verifica se o usuário já existe
    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM usuarios WHERE id_telegram = ?", (id_telegram,))
    usuario = cursor.fetchone()

    # Se não existir, cria com saldo 0
    if not usuario:
        cursor.execute("INSERT INTO usuarios (id_telegram, nome, saldo) VALUES (?, ?, ?)",
                       (id_telegram, nome, 0))
        conn.commit()

    conn.close()

    # Mensagem de boas-vindas
    mensagem = (
        "✅ Acesso liberado com sucesso\n"
        f"👤 Nome: {nome}\n"
        f"🆔 ID: {id_telegram}"
    )

    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text(text=mensagem)
    else:
        await update.message.reply_text(mensagem)

# Início do bot
if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()

    TOKEN = os.environ["BOT_TOKEN"]
    app = ApplicationBuilder().token(TOKEN).build()

    # Comandos
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("acessar", acessar))

    # Callback para botão "Acessar"
    from telegram.ext import CallbackQueryHandler
    app.add_handler(CallbackQueryHandler(acessar, pattern="^acessar$"))

    print("Bot rodando...")
    app.run_polling()
