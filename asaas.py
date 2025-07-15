import os
import requests
import sqlite3
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

ASAAS_API_KEY = os.getenv("ASAAS_API_KEY")
DB_PATH = "apostas.db"
ASAAS_ENDPOINT = "https://api.asaas.com/api/v3"

def conectar():
    return sqlite3.connect(DB_PATH)

def criar_cliente_asaas(user_id, nome):
    url = f"{ASAAS_ENDPOINT}/customers"
    headers = {"Authorization": f"Bearer {ASAAS_API_KEY}"}
    data = {
        "name": f"User_{user_id}_{nome}",
        "cpfCnpj": "00000000000",
        "email": f"user{user_id}@telegram.com"
    }
    r = requests.post(url, headers=headers, json=data)
    if r.status_code in [200, 201]:
        return r.json()["id"]
    else:
        print("Erro ao criar cliente:", r.text)
        return None

def criar_cobranca_pix(cliente_id, valor):
    url = f"{ASAAS_ENDPOINT}/payments"
    headers = {"Authorization": f"Bearer {ASAAS_API_KEY}"}
    data = {
        "customer": cliente_id,
        "billingType": "PIX",
        "value": valor,
        "dueDate": "2025-12-31",
        "description": "Depósito Telegram Bet"
    }
    r = requests.post(url, headers=headers, json=data)
    if r.status_code in [200, 201]:
        resposta = r.json()
        return resposta["id"], resposta["invoiceUrl"]
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

async def mostrar_opcoes_deposito(update, context):
    keyboard = [
        [InlineKeyboardButton("R$ 5", callback_data="dep_5"),
         InlineKeyboardButton("R$ 10", callback_data="dep_10")],
        [InlineKeyboardButton("R$ 20", callback_data="dep_20"),
         InlineKeyboardButton("R$ 50", callback_data="dep_50")],
        [InlineKeyboardButton("R$ 100", callback_data="dep_100"),
         InlineKeyboardButton("R$ 500", callback_data="dep_500")],
        [InlineKeyboardButton("R$ 1000", callback_data="dep_1000")],
        [InlineKeyboardButton("Outro valor", callback_data="dep_custom")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Escolha o valor para depositar:", reply_markup=reply_markup)

async def deposito_callback(update, context):
    query = update.callback_query
    await query.answer()
    data = query.data
    if data.startswith("dep_"):
        valor_str = data.split("_")[1]
        if valor_str == "custom":
            await query.edit_message_text("Digite o valor que deseja depositar (mínimo R$5):")
            context.user_data["awaiting_deposit_value"] = True
        else:
            valor = float(valor_str)
            await gerar_cobranca(update, context, valor)

async def receber_valor_manual(update, context):
    if context.user_data.get("awaiting_deposit_value"):
        texto = update.message.text.strip().replace(",", ".")
        try:
            valor = float(texto)
            if valor < 5:
                await update.message.reply_text("O valor mínimo é R$5. Tente novamente:")
                return
            context.user_data["awaiting_deposit_value"] = False
            await gerar_cobranca(update, context, valor)
        except:
            await update.message.reply_text("Valor inválido. Digite um número como 10, 25.50, etc:")

async def gerar_cobranca(update_or_query, context, valor):
    if hasattr(update_or_query, "from_user"):
        user = update_or_query.from_user
    else:
        user = update_or_query.callback_query.from_user

    user_id = user.id
    nome = user.first_name

    cliente_id = criar_cliente_asaas(user_id, nome)
    if not cliente_id:
        await update_or_query.message.reply_text("Erro ao criar cobrança. Tente novamente mais tarde.")
        return

    payment_id, link = criar_cobranca_pix(cliente_id, valor)
    if not payment_id:
        await update_or_query.message.reply_text("Erro ao gerar cobrança Pix.")
        return

    adicionar_pagamento(user_id, payment_id, valor)

    mensagem = f"Para depositar R${valor:.2f}, clique no botão abaixo para pagar via Pix:"
    keyboard = [
        [InlineKeyboardButton("Pagar agora 💸", url=link)],
        [InlineKeyboardButton("✅ Já paguei", callback_data=f"verificar_{payment_id}")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    if hasattr(update_or_query, "edit_message_text"):
        await update_or_query.edit_message_text(mensagem, reply_markup=reply_markup)
    else:
        await update_or_query.message.reply_text(mensagem, reply_markup=reply_markup)

async def verificar_pagamento(update, context):
    query = update.callback_query
    await query.answer()
    data = query.data
    if data.startswith("verificar_"):
        payment_id = data.split("_")[1]
        url = f"{ASAAS_ENDPOINT}/payments/{payment_id}"
        headers = {"Authorization": f"Bearer {ASAAS_API_KEY}"}
        r = requests.get(url, headers=headers)
        if r.status_code == 200:
            status = r.json().get("status")
            user_id = query.from_user.id
            valor = float(r.json().get("value", 0))
            if status == "CONFIRMED":
                conn = conectar()
                cursor = conn.cursor()
                cursor.execute("UPDATE pagamentos SET status = ? WHERE payment_id = ?", (status, payment_id))
                cursor.execute("SELECT saldo FROM usuarios WHERE id_telegram = ?", (user_id,))
                row = cursor.fetchone()
                saldo_atual = float(row[0]) if row else 0.0
                novo_saldo = saldo_atual + valor
                cursor.execute("UPDATE usuarios SET saldo = ? WHERE id_telegram = ?", (novo_saldo, user_id))
                conn.commit()
                conn.close()
                await query.edit_message_text("✅ Pagamento confirmado! Saldo atualizado com sucesso.")
            elif status == "PENDING":
                await query.edit_message_text("Pagamento ainda está pendente. Aguarde alguns minutos.")
            else:
                await query.edit_message_text(f"Status do pagamento: {status}")
        else:
            await query.edit_message_text("Erro ao consultar o pagamento. Tente mais tarde.")
