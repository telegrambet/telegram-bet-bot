import os
import sqlite3
import requests
from telegram import Update, ReplyKeyboardMarkup, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

# Banco SQLite
DB_PATH = "apostas.db"

def conectar():
    return sqlite3.connect(DB_PATH)

# Criar tabela pagamentos (executar só uma vez)
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

criar_tabela_pagamentos()

# Função para criar cobrança Pix Mercado Pago
MP_ACCESS_TOKEN = os.getenv("MP_ACCESS_TOKEN")

def criar_cobranca_pix(valor, external_reference):
    url = "https://api.mercadopago.com/v1/payments"
    headers = {
        "Authorization": f"Bearer {MP_ACCESS_TOKEN}",
        "Content-Type": "application/json",
    }
    data = {
        "transaction_amount": valor,
        "payment_method_id": "pix",
        "description": "Depósito no Telegram Bet",
        "external_reference": str(external_reference),
        "payer": {"email": "usuario@example.com"},
    }
    r = requests.post(url, json=data, headers=headers)
    if r.status_code == 201:
        pagamento = r.json()
        pix_info = pagamento["point_of_interaction"]["transaction_data"]
        qr_code = pix_info["qr_code"]
        payment_id = pagamento["id"]
        return qr_code, payment_id
    else:
        print("Erro ao criar cobrança:", r.text)
        return None, None

# Função para atualizar status pagamento no DB
def atualizar_pagamento(payment_id, status):
    conn = conectar()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE pagamentos SET status = ? WHERE payment_id = ?", (status, payment_id)
    )
    conn.commit()
    conn.close()

# Função para buscar pagamento pelo payment_id
def buscar_pagamento(payment_id):
    conn = conectar()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM pagamentos WHERE payment_id = ?", (payment_id,))
    pagamento = cursor.fetchone()
    conn.close()
    return pagamento

# Função para adicionar pagamento no DB
def adicionar_pagamento(id_telegram, payment_id, valor):
    conn = conectar()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO pagamentos (id_telegram, payment_id, valor, status) VALUES (?, ?, ?, ?)",
        (id_telegram, payment_id, valor, "pending"),
    )
    conn.commit()
    conn.close()

# Função para pegar saldo do usuário
def pegar_saldo(id_telegram):
    conn = conectar()
    cursor = conn.cursor()
    cursor.execute("SELECT saldo FROM usuarios WHERE id_telegram = ?", (id_telegram,))
    res = cursor.fetchone()
    conn.close()
    if res:
        return float(res[0])
    else:
        return 0.0

# Função para atualizar saldo do usuário (soma)
def atualizar_saldo(id_telegram, valor):
    saldo_atual = pegar_saldo(id_telegram)
    novo_saldo = saldo_atual + valor
    conn = conectar()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE usuarios SET saldo = ? WHERE id_telegram = ?", (novo_saldo, id_telegram)
    )
    conn.commit()
    conn.close()

# Comando /start (login + boas-vindas)
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    nome = update.effective_user.first_name
    id_telegram = update.effective_user.id

    conn = conectar()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM usuarios WHERE id_telegram = ?", (id_telegram,))
    usuario = cursor.fetchone()

    if not usuario:
        cursor.execute(
            "INSERT INTO usuarios (id_telegram, nome, saldo) VALUES (?, ?, ?)",
            (id_telegram, nome, 0),
        )
        conn.commit()
        saldo = 0.0
    else:
        try:
            saldo = float(usuario[2])
        except (IndexError, TypeError, ValueError):
            saldo = 0.0

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
        ["🎟 Meus bilhetes", "📊 Processado"],
    ]
    reply_markup = ReplyKeyboardMarkup(botoes, resize_keyboard=True)

    await update.message.reply_text(mensagem, reply_markup=reply_markup)

# Botão "Depositar" — mostra opções de valores
async def mostrar_opcoes_deposito(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("R$ 5,00", callback_data="deposit_5")],
        [InlineKeyboardButton("R$ 10,00", callback_data="deposit_10")],
        [InlineKeyboardButton("R$ 20,00", callback_data="deposit_20")],
        [InlineKeyboardButton("R$ 50,00", callback_data="deposit_50")],
        [InlineKeyboardButton("R$ 100,00", callback_data="deposit_100")],
        [InlineKeyboardButton("R$ 500,00", callback_data="deposit_500")],
        [InlineKeyboardButton("R$ 1.000,00", callback_data="deposit_1000")],
        [InlineKeyboardButton("Digite outro valor", callback_data="deposit_custom")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Escolha o valor para depositar:", reply_markup=reply_markup)

# Callback para opções de depósito
async def deposito_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data.startswith("deposit_"):
        valor_str = data.split("_")[1]
        if valor_str == "custom":
            await query.edit_message_text("Digite o valor que deseja depositar (mínimo R$5,00):")
            context.user_data["awaiting_deposit_value"] = True
        else:
            valor = int(valor_str)
            await criar_e_enviar_cobranca(query, context, valor)

# Receber valor digitado customizado
async def receber_valor_deposito(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get("awaiting_deposit_value"):
        texto = update.message.text.replace(",", ".").strip()
        try:
            valor = float(texto)
            if valor < 5:
                await update.message.reply_text("O valor mínimo para depósito é R$5,00. Tente novamente:")
                return
            await criar_e_enviar_cobranca(update, context, valor)
            context.user_data["awaiting_deposit_value"] = False
        except ValueError:
            await update.message.reply_text(
                "Valor inválido. Digite um número válido (ex: 20, 50, 100):"
            )

# Criar cobrança e enviar para o usuário
async def criar_e_enviar_cobranca(update_or_query, context, valor):
    user_id = update_or_query.from_user.id
    qr_code, payment_id = criar_cobranca_pix(valor, external_reference=user_id)
    if qr_code:
        adicionar_pagamento(user_id, payment_id, valor)

        mensagem = (
            f"Para depositar R${valor:.2f}, pague via Pix usando o código abaixo:\n\n{qr_code}\n\n"
            "Quando pagar, clique no botão abaixo para confirmar."
        )

        keyboard = [
            [InlineKeyboardButton("Já paguei", callback_data=f"checkpay_{payment_id}")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        if hasattr(update_or_query, "edit_message_text"):
            await update_or_query.edit_message_text(mensagem, reply_markup=reply_markup)
        else:
            await update_or_query.message.reply_text(mensagem, reply_markup=reply_markup)
    else:
        if hasattr(update_or_query, "edit_message_text"):
            await update_or_query.edit_message_text("Erro ao gerar cobrança. Tente novamente mais tarde.")
        else:
            await update_or_query.message.reply_text("Erro ao gerar cobrança. Tente novamente mais tarde.")

# Botão "Já paguei" - verifica pagamento Mercado Pago
async def check_payment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data.startswith("checkpay_"):
        payment_id = data.split("_")[1]

        url = f"https://api.mercadopago.com/v1/payments/{payment_id}"
        headers = {"Authorization": f"Bearer {MP_ACCESS_TOKEN}"}
        r = requests.get(url, headers=headers)

        if r.status_code == 200:
            pagamento = r.json()
            status = pagamento.get("status")
            user_id = int(pagamento.get("external_reference"))

            pagamento_db = buscar_pagamento(payment_id)

            if pagamento_db and pagamento_db[4] != status:  # índice 4 = status
                atualizar_pagamento(payment_id, status)
                if status == "approved":
                    atualizar_saldo(user_id, float(pagamento_db[3]))  # índice 3 = valor
                    await query.edit_message_text("Pagamento aprovado! Saldo atualizado com sucesso.")
                elif status in ["pending", "in_process"]:
                    await query.edit_message_text("Pagamento ainda não confirmado. Por favor, aguarde.")
                else:
                    await query.edit_message_text(f"Pagamento com status: {status}.")
            else:
                await query.edit_message_text("Pagamento já está atualizado ou não encontrado.")
        else:
            await query.edit_message_text("Erro ao consultar pagamento. Tente novamente mais tarde.")

# Handler para detectar texto digitado para valor customizado
async def handler_texto(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await receber_valor_deposito(update, context)

# Início do bot
if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()

    TOKEN = os.getenv("BOT_TOKEN")
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("depositar", mostrar_opcoes_deposito))
    app.add_handler(CallbackQueryHandler(deposito_callback, pattern="^deposit_"))
    app.add_handler(CallbackQueryHandler(check_payment, pattern="^checkpay_"))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handler_texto))

    print("Bot rodando...")
    app.run_polling()
