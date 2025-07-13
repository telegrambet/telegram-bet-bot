import os
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
import sqlite3

# Função para conectar ao banco de dados
def conectar():
    return sqlite3.connect("apostas.db")

# Comando /start (também registra e faz login)
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    nome = update.effective_user.first_name
    id_telegram = update.effective_user.id

    # Conecta ao banco e verifica se já existe
    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM usuarios WHERE id_telegram = ?", (id_telegram,))
    usuario = cursor.fetchone()

    # Se não existir, cadastra com saldo 0
    if not usuario:
        cursor.execute(
            "INSERT INTO usuarios (id_telegram, nome, saldo) VALUES (?, ?, ?)",
            (id_telegram, nome, 0)
        )
        conn.commit()

    conn.close()

    # Mensagem final com boas-vindas e dados
    mensagem = (
        "Fala jogador! ⚽🥇 Bem-vindo ao Telegram Bet! A Bet OFICIAL no telegram\n\n"
        "✅ Acesso liberado com sucesso\n"
        f"👤 Nome: {nome}\n"
        f"🆔 ID: {id_telegram}"
    )

    await update.message.reply_text(mensagem)

# Início do bot
if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()

    TOKEN = os.environ["BOT_TOKEN"]
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))

    print("Bot rodando...")
    app.run_polling()
  
