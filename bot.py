import os
import sqlite3
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    CallbackQueryHandler,
    MessageHandler,
    filters
)
from asaas import (
    mostrar_opcoes_deposito,
    deposito_callback,
    receber_valor_manual,
    verificar_pagamento
)

DB_PATH = "apostas.db"

def conectar():
    return sqlite3.connect(DB_PATH)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    nome = update.effective_user.first_name
    id_telegram = update.effective_user.id

    conn = conectar()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM usuarios WHERE id_telegram = ?", (id_telegram,))
    usuario = cursor.fetchone()

    if not usuario:
        cursor.execute("INSERT INTO usuarios (id_telegram, nome, saldo) VALUES (?, ?, ?)", (id_telegram, nome, 0))
        conn.commit()
        saldo = 0
    else:
        try:
            saldo = float(usuario[2])
        except (IndexError, TypeError, ValueError):
            saldo = 0

    conn.close()

    mensagem = (
        "Fala jogador! ⚽🥇 Bem-vindo ao Telegram Bet! A Bet OFICIAL no telegram\n\n"
        "✅ Acesso liberado com sucesso\n"
        f"👤 Nome: {nome}\n"
        f"🆔 ID: {id_telegram}\n"
        f"💵 Saldo: R$ {saldo:.2f}"
    )

    botoes = [
        ["💰 Depositar", "💸 Saque"],
        ["📅 Jogos de amanhã", "📆 Jogos do dia"],
        ["🔴 Jogos ao vivo"],
        ["🎟 Meus bilhetes", "📊 Processado"]
    ]
    reply_markup = ReplyKeyboardMarkup(botoes, resize_keyboard=True)

    await update.message.reply_text(mensagem, reply_markup=reply_markup)

def criar_tabela_pagamentos():
    conn = conectar()
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

if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()

    TOKEN = os.environ["BOT_TOKEN"]
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(deposito_callback, pattern="^dep_"))
    app.add_handler(CallbackQueryHandler(verificar_pagamento, pattern="^verificar_"))
    app.add_handler(MessageHandler(filters.TEXT & filters.Regex("💰 Depositar"), mostrar_opcoes_deposito))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), receber_valor_manual))

    print("🤖 Bot rodando...")
    app.run_polling()
    
