import os
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
import sqlite3

# Função para conectar ao banco de dados
def conectar():
    return sqlite3.connect("apostas.db")

# Comando /start (também faz o login)
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
        cursor.execute("INSERT INTO usuarios (id_telegram, nome, saldo) VALUES (?, ?, ?)",
                       (id_telegram, nome, 0))
        conn.commit()
        saldo = 0
    else:
        saldo = usuario[2]  # índice 2 = campo "saldo"

    conn.close()

    # Mensagem com saldo incluído
    mensagem = (
        "Fala jogador(a)! ⚽🥇 Bem-vindo ao Telegram Bet!\n\n"
         "A Bet OFICIAL no telegram\n\n"
         
        "✅ Acesso liberado com sucesso\n"
        f"👤 Nome: {nome}\n"
        f"🆔 ID: {id_telegram}\n"
        f"💵 Saldo: R$ {saldo:.2f}"
    )

    # Botões do menu principal
    botoes = [
        ["💰 Depositar", "💸 Saque"],
        ["📅 Jogos de amanhã", "📆 Jogos do dia"],
        ["🔴 Jogos ao vivo"],
        ["🎟 Meus bilhetes", "📊 Processado"]
    ]
    reply_markup = ReplyKeyboardMarkup(botoes, resize_keyboard=True)

    await update.message.reply_text(mensagem, reply_markup=reply_markup)


# ⚠️ Criar tabela pagamentos (executa só uma vez)
def criar_tabela_pagamentos():
    conn = sqlite3.connect("apostas.db")
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS pagamentos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            id_telegram INTEGER,
            payment_id TEXT,
            valor REAL,
            status TEXT,
            data_criacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()
    print("✅ Tabela pagamentos criada com sucesso!")

criar_tabela_pagamentos()

# Início do bot
if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()

    TOKEN = os.environ["BOT_TOKEN"]
    app = ApplicationBuilder().token(TOKEN).build()

    # /start é o único comando necessário
    app.add_handler(CommandHandler("start", start))

    print("Bot rodando...")
    app.run_polling()
