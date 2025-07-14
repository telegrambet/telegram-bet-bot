from telegram import InlineKeyboardButton, InlineKeyboardMarkup

import requests
import os
import sqlite3

MP_ACCESS_TOKEN = os.getenv("MP_ACCESS_TOKEN")
DB_PATH = "apostas.db"

def conectar():
    return sqlite3.connect(DB_PATH)

# Criar cobrança Pix Mercado Pago
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

def adicionar_pagamento(id_telegram, payment_id, valor):
    conn = conectar()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO pagamentos (id_telegram, payment_id, valor, status) VALUES (?, ?, ?, ?)",
        (id_telegram, payment_id, valor, "pending"),
    )
    conn.commit()
    conn.close()

# Handler do botão Depositar (exibir opções)
async def mostrar_opcoes_deposito(update, context):
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

# Callback para tratar seleção do valor
async def deposito_callback(update, context):
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

# Receber valor digitado pelo usuário
async def receber_valor_deposito(update, context):
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
            await update.message.reply_text("Valor inválido. Digite um número válido (ex: 20, 50, 100):")

# Criar cobrança e enviar QR code
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

# Callback para botão "Já paguei"
async def check_payment(update, context):
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

            conn = conectar()
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM pagamentos WHERE payment_id = ?", (payment_id,))
            pagamento_db = cursor.fetchone()
            conn.close()

            if pagamento_db and pagamento_db[4] != status:  # índice 4 = status
                conn = conectar()
                cursor = conn.cursor()
                cursor.execute(
                    "UPDATE pagamentos SET status = ? WHERE payment_id = ?", (status, payment_id)
                )
                conn.commit()
                conn.close()

                if status == "approved":
                    conn = conectar()
                    cursor = conn.cursor()
                    cursor.execute("SELECT saldo FROM usuarios WHERE id_telegram = ?", (user_id,))
                    res = cursor.fetchone()
                    saldo_atual = float(res[0]) if res else 0.0
                    novo_saldo = saldo_atual + float(pagamento_db[3])
                    cursor.execute(
                        "UPDATE usuarios SET saldo = ? WHERE id_telegram = ?", (novo_saldo, user_id)
                    )
                    conn.commit()
                    conn.close()
                    await query.edit_message_text("Pagamento aprovado! Saldo atualizado com sucesso.")
                elif status in ["pending", "in_process"]:
                    await query.edit_message_text("Pagamento ainda não confirmado. Por favor, aguarde.")
                else:
                    await query.edit_message_text(f"Pagamento com status: {status}.")
            else:
                await query.edit_message_text("Pagamento já está atualizado ou não encontrado.")
        else:
            await query.edit_message_text("Erro ao consultar pagamento. Tente novamente mais tarde.")
