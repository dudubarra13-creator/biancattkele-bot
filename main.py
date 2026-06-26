import base64
import os
import re
import time
from datetime import date

import requests
from flask import Flask, request

app = Flask(__name__)

# Telegram
BOT_TOKEN = os.environ.get("BOT_TOKEN", "").strip()
WEBHOOK_SECRET = os.environ.get("WEBHOOK_SECRET", "biancattkele123").strip()
TELEGRAM_API = f"https://api.telegram.org/bot{BOT_TOKEN}"

# Asaas
ASAAS_API_KEY = os.environ.get("ASAAS_API_KEY", "").strip()
ASAAS_BASE_URL = os.environ.get("ASAAS_BASE_URL", "https://api.asaas.com/v3").rstrip("/")
ASAAS_WEBHOOK_TOKEN = os.environ.get("ASAAS_WEBHOOK_TOKEN", "").strip()

# Produto
PACK_NAME = os.environ.get("PACK_NAME", "Acesso às 12 fotos reservadas").strip()
PACK_PRICE = float(os.environ.get("PACK_PRICE", "14.90").replace(",", "."))
PACK_LINK = os.environ.get("PACK_LINK", "").strip()

PREVIEW_PHOTO_FILE_ID = os.environ.get("PREVIEW_PHOTO_FILE_ID", "").strip()

# Memória temporária
USER_STATE = {}
ORDERS = {}
PROCESSED_EVENTS = set()
DELIVERED_PAYMENTS = set()

PAID_STATUSES = {"RECEIVED", "CONFIRMED"}


def telegram(method, payload=None, files=None, data=None):
    try:
        if files:
            response = requests.post(
                f"{TELEGRAM_API}/{method}",
                data=data or {},
                files=files,
                timeout=30
            )
        else:
            response = requests.post(
                f"{TELEGRAM_API}/{method}",
                json=payload or {},
                timeout=20
            )

        try:
            return response.json()
        except Exception:
            return {"ok": False, "raw": response.text}
    except Exception as error:
        print("Telegram error:", error)
        return {"ok": False, "error": str(error)}


def send_message(chat_id, text, keyboard=None):
    payload = {
        "chat_id": chat_id,
        "text": text
    }

    if keyboard:
        payload["reply_markup"] = {
            "inline_keyboard": keyboard
        }

    return telegram("sendMessage", payload=payload)


def send_photo_file_id(chat_id, file_id, caption=None):
    payload = {
        "chat_id": chat_id,
        "photo": file_id
    }
    if caption:
        payload["caption"] = caption
    return telegram("sendPhoto", payload=payload)


def send_photo_bytes(chat_id, image_bytes, caption=None):
    data = {"chat_id": chat_id}
    if caption:
        data["caption"] = caption

    files = {
        "photo": ("pix.png", image_bytes, "image/png")
    }

    return telegram("sendPhoto", files=files, data=data)


def answer_callback(callback_id):
    if callback_id:
        telegram("answerCallbackQuery", payload={"callback_query_id": callback_id})


def asaas_headers(has_body=True):
    headers = {
        "accept": "application/json",
        "access_token": ASAAS_API_KEY,
        "User-Agent": "BotBiancaMonteiro/1.0"
    }

    if has_body:
        headers["content-type"] = "application/json"

    return headers


def asaas_error_text(data):
    if isinstance(data, dict) and data.get("errors"):
        return "; ".join(
            item.get("description", "Erro sem descrição")
            for item in data["errors"]
        )
    return str(data)


def asaas_request(method, path, json_body=None):
    if not ASAAS_API_KEY:
        raise RuntimeError("ASAAS_API_KEY não configurada no Render.")

    url = f"{ASAAS_BASE_URL}{path}"

    response = requests.request(
        method,
        url,
        headers=asaas_headers(has_body=json_body is not None),
        json=json_body,
        timeout=30
    )

    try:
        data = response.json()
    except Exception:
        data = {"raw": response.text}

    if response.status_code < 200 or response.status_code >= 300:
        raise RuntimeError(f"Asaas HTTP {response.status_code}: {asaas_error_text(data)}")

    return data


def clean_document(value):
    return re.sub(r"\D", "", value or "")


def money_br(value):
    return f"R$ {value:.2f}".replace(".", ",")


def main_menu_keyboard():
    return [
        [{"text": "👀 Quer ver uma prévia?", "callback_data": "see_photos"}],
        [{"text": f"🔥 12 fotos quentes da Bianca - {money_br(PACK_PRICE)}", "callback_data": "buy_pack"}],
        [{"text": "💎 Lista VIP", "callback_data": "vip_list"}],
        [{"text": "📜 Termos do acesso", "callback_data": "terms"}],
        [{"text": "💬 Suporte", "callback_data": "support"}],
    ]


def main_menu_keyboard():
    return [
        [{"text": "👀 Ver fotos disponíveis", "callback_data": "see_photos"}],
        [{"text": "💋 Liberar acesso às 12 fotos", "callback_data": "buy_pack"}],
        [{"text": "💎 Lista VIP", "callback_data": "vip_list"}],
        [{"text": "📜 Termos do acesso", "callback_data": "terms"}],
        [{"text": "💬 Suporte", "callback_data": "support"}],
    ]


def back_keyboard():
    return [
        [{"text": "⬅️ Voltar ao menu", "callback_data": "back_menu"}]
    ]


def buy_keyboard():
    return [
        [{"text": f"✅ Gerar Pix de {money_br(PACK_PRICE)}", "callback_data": "start_pix"}],
        [{"text": "⬅️ Voltar", "callback_data": "back_menu"}],
    ]


def check_payment_keyboard(payment_id):
    return [
        [{"text": "✅ Já paguei", "callback_data": f"check_{payment_id}"}],
        [{"text": "💬 Suporte", "callback_data": "support"}],
    ]


@app.get("/")
def home():
    return "Bot Bianca Monteiro online ✅"


def send_start(chat_id):
    USER_STATE.pop(chat_id, None)

    text = (
        "💋 Você chegou no lado mais reservado da Bianca Monteiro.\n\n"
        "Antes de continuar, preciso confirmar uma coisa:\n\n"
        "Este acesso é exclusivo para maiores de 18 anos e contém fotos "
        "sensuais, íntimas e reservadas, sem nudez explícita.\n\n"
        "Se você tem 18 anos ou mais, toque no botão abaixo para continuar 🔞"
    )

    send_message(chat_id, text, age_gate_keyboard())


def send_main_menu(chat_id):
    USER_STATE.pop(chat_id, None)

    text = (
        "Acesso liberado 💋\n\n"
        "A Bianca separou fotos que não aparecem nas redes, com uma estética "
        "mais íntima, sensual e exclusiva.\n\n"
        "Escolha uma opção abaixo:"
    )

    send_message(chat_id, text, main_menu_keyboard())


def send_photos_preview(chat_id):
    if PREVIEW_PHOTO_FILE_ID:
        send_photo_file_id(
            chat_id,
            PREVIEW_PHOTO_FILE_ID,
            caption="Uma prévia discreta do que a Bianca separou pra você 👀💋"
        )
    else:
        send_message(
            chat_id,
            "A prévia ainda está sendo preparada 👀💋"
        )

    text = (
        "Gostou da prévia? 💋\n\n"
        "As 12 fotos completas são mais íntimas, sensuais e reservadas, "
        "feitas para quem quer ver um lado da Bianca que não aparece nas redes.\n\n"
        "Conteúdo adulto, sem nudez explícita, com entrega automática após confirmação do Pix."
    )

    send_message(chat_id, text, [
        [{"text": f"🔥 Quero as 12 fotos - {money_br(PACK_PRICE)}", "callback_data": "buy_pack"}],
        [{"text": "⬅️ Voltar", "callback_data": "back_menu"}],
    ])


def send_buy_offer(chat_id):
    text = (
        f"💋 {PACK_NAME}\n\n"
        "Você recebe:\n"
        "• 12 fotos sensuais e exclusivas\n"
        "• entrega discreta pelo Telegram\n"
        "• acesso direto após confirmação do Pix\n\n"
        f"Valor de teste: {money_br(PACK_PRICE)}\n\n"
        "Toque abaixo para continuar."
    )

    send_message(chat_id, text, buy_keyboard())


def start_pix_flow(chat_id):
    USER_STATE[chat_id] = {"step": "waiting_name"}

    text = (
        "Perfeito 💋\n\n"
        "Para gerar seu Pix com segurança, me envie o primeiro nome do pagador:"
    )

    send_message(chat_id, text, back_keyboard())


def create_asaas_customer(name, cpf_cnpj, chat_id):
    body = {
        "name": name[:100],
        "cpfCnpj": clean_document(cpf_cnpj),
        "externalReference": f"telegram_customer_{chat_id}",
        "notificationDisabled": True,
        "groupName": "Telegram Bianca Monteiro"
    }

    customer = asaas_request("POST", "/customers", body)
    return customer["id"]


def create_asaas_payment(customer_id, chat_id):
    external_reference = f"tg_{chat_id}_{int(time.time())}"

    body = {
        "customer": customer_id,
        "billingType": "PIX",
        "value": PACK_PRICE,
        "dueDate": date.today().isoformat(),
        "description": "Acesso digital Bianca Monteiro",
        "externalReference": external_reference
    }

    payment = asaas_request("POST", "/payments", body)
    payment["externalReference"] = external_reference
    return payment


def get_pix_qr_code(payment_id):
    return asaas_request("GET", f"/payments/{payment_id}/pixQrCode")


def send_pix_to_user(chat_id, payment, qr_code):
    payment_id = payment["id"]
    pix_payload = qr_code.get("payload") or qr_code.get("copyPaste") or ""
    encoded_image = qr_code.get("encodedImage") or qr_code.get("base64") or ""

    intro = (
        "Pix gerado com sucesso ✅\n\n"
        f"Valor: {money_br(PACK_PRICE)}\n"
        "Depois do pagamento, a confirmação pode chegar automaticamente em alguns instantes.\n\n"
        "Você também pode tocar em “Já paguei” para eu consultar."
    )

    send_message(chat_id, intro)

    if encoded_image:
        try:
            if "," in encoded_image:
                encoded_image = encoded_image.split(",", 1)[1]
            image_bytes = base64.b64decode(encoded_image)
            send_photo_bytes(chat_id, image_bytes, caption="📷 QR Code Pix")
        except Exception as error:
            print("QR image error:", error)

    if pix_payload:
        send_message(
            chat_id,
            "Pix copia e cola 👇\n\n" + pix_payload,
            check_payment_keyboard(payment_id)
        )
    else:
        invoice_url = payment.get("invoiceUrl")
        if invoice_url:
            send_message(
                chat_id,
                "Não consegui exibir o copia e cola, mas você pode pagar pela fatura:\n\n"
                + invoice_url,
                check_payment_keyboard(payment_id)
            )
        else:
            send_message(
                chat_id,
                "Não consegui recuperar o Pix copia e cola agora. Toque em suporte.",
                check_payment_keyboard(payment_id)
            )


def process_pix_creation(chat_id, name, cpf_cnpj):
    send_message(chat_id, "Estou gerando seu Pix agora... só um instante 💋")

    customer_id = create_asaas_customer(name, cpf_cnpj, chat_id)
    payment = create_asaas_payment(customer_id, chat_id)
    qr_code = get_pix_qr_code(payment["id"])

    ORDERS[payment["id"]] = {
        "chat_id": chat_id,
        "customer_id": customer_id,
        "status": payment.get("status", "PENDING"),
        "externalReference": payment.get("externalReference")
    }

    send_pix_to_user(chat_id, payment, qr_code)


def parse_chat_id_from_external_reference(external_reference):
    match = re.search(r"tg_(\d+)_", external_reference or "")
    if not match:
        return None
    return int(match.group(1))


def deliver_pack(chat_id, payment_id=None):
    if payment_id and payment_id in DELIVERED_PAYMENTS:
        return

    if payment_id:
        DELIVERED_PAYMENTS.add(payment_id)

    send_message(
        chat_id,
        "Pagamento confirmado ✅💋\n\n"
        "Seu acesso foi liberado. Obrigado por entrar no lado mais reservado da Bianca."
    )

    if PACK_PHOTO_FILE_IDS:
        for index, file_id in enumerate(PACK_PHOTO_FILE_IDS, start=1):
            caption = f"Foto {index}/12 💋" if index == 1 else None
            send_photo_file_id(chat_id, file_id, caption=caption)
        return

    if PACK_LINK:
        send_message(
            chat_id,
            "Aqui está seu acesso às fotos reservadas 👇\n\n" + PACK_LINK
        )
        return

    send_message(
        chat_id,
        "A entrega automática ainda não tem PACK_LINK ou PACK_PHOTO_FILE_IDS configurado no Render.\n\n"
        "Para teste, o pagamento já foi reconhecido. Agora configure a entrega das fotos."
    )


def check_payment(chat_id, payment_id):
    try:
        payment = asaas_request("GET", f"/payments/{payment_id}")
        status = payment.get("status", "")

        if status in PAID_STATUSES:
            deliver_pack(chat_id, payment_id)
        else:
            send_message(
                chat_id,
                "Ainda não encontrei a confirmação do pagamento.\n\n"
                f"Status atual: {status or 'aguardando'}\n\n"
                "Se você acabou de pagar, aguarde alguns instantes e toque em “Já paguei” novamente.",
                check_payment_keyboard(payment_id)
            )

    except Exception as error:
        print("Check payment error:", error)
        send_message(
            chat_id,
            "Não consegui consultar o pagamento agora. Tente novamente em alguns instantes ou chame o suporte."
        )


def handle_callback(chat_id, callback_id, data):
    answer_callback(callback_id)

    if data == "confirm_18":
        send_main_menu(chat_id)

    elif data == "exit":
        send_message(
            chat_id,
            "Tudo bem. Este conteúdo é apenas para maiores de 18 anos. 🔞"
        )

    elif data == "see_photos":
        send_photos_preview(chat_id)

    elif data == "buy_pack":
        send_buy_offer(chat_id)

    elif data == "start_pix":
        start_pix_flow(chat_id)

    elif data.startswith("check_"):
        payment_id = data.replace("check_", "", 1)
        check_payment(chat_id, payment_id)

    elif data == "vip_list":
        text = (
            "💎 Lista VIP Bianca\n\n"
            "O VIP completo ainda não abriu.\n\n"
            "Quem entrar na lista vai receber aviso antes, condições de lançamento "
            "e prioridade nos próximos conteúdos.\n\n"
            "Por enquanto, me envie uma mensagem escrita: QUERO VIP."
        )
        send_message(chat_id, text, back_keyboard())

    elif data == "terms":
        text = (
            "📜 Termos do acesso\n\n"
            "• Conteúdo permitido apenas para maiores de 18 anos.\n"
            "• Fotos sensuais adultas, sem nudez explícita.\n"
            "• Conteúdo digital de acesso individual.\n"
            "• Não é permitido revender, publicar ou redistribuir.\n"
            "• Após a confirmação do pagamento, o acesso é liberado pelo Telegram.\n\n"
            "Ao continuar, você confirma que tem 18 anos ou mais."
        )
        send_message(chat_id, text, back_keyboard())

    elif data == "support":
        text = (
            "💬 Suporte\n\n"
            "Me envie sua dúvida aqui no chat.\n"
            "Se for sobre pagamento ou acesso, escreva com calma que eu te ajudo."
        )
        send_message(chat_id, text, back_keyboard())

    elif data == "back_menu":
        send_main_menu(chat_id)

    else:
        send_main_menu(chat_id)


def handle_text_message(chat_id, text):
    normalized = (text or "").strip().lower()

    if normalized in ["/start", "start", "começar"]:
        send_start(chat_id)
        return

    state = USER_STATE.get(chat_id)

    if state and state.get("step") == "waiting_name":
        name = text.strip()

        if len(name) < 2:
            send_message(chat_id, "Me envie um nome válido para continuar.")
            return

        USER_STATE[chat_id] = {
            "step": "waiting_document",
            "name": name
        }

        send_message(
            chat_id,
            "Agora envie apenas os números do CPF ou CNPJ do pagador para gerar o Pix:"
        )
        return

    if state and state.get("step") == "waiting_document":
        document = clean_document(text)

        if len(document) not in [11, 14]:
            send_message(
                chat_id,
                "Documento inválido. Envie apenas os números do CPF ou CNPJ."
            )
            return

        name = state["name"]
        USER_STATE.pop(chat_id, None)

        try:
            process_pix_creation(chat_id, name, document)
        except Exception as error:
            print("Pix creation error:", error)
            send_message(
                chat_id,
                "Não consegui gerar o Pix agora.\n\n"
                "Confira se a chave ASAAS_API_KEY está correta no Render e se a conta Asaas está liberada para cobranças Pix.\n\n"
                f"Erro técnico: {str(error)[:700]}"
            )
        return

    if normalized in ["/pack", "pack", "fotos"]:
        send_main_menu(chat_id)

    elif normalized in ["/vip", "quero vip"]:
        send_message(
            chat_id,
            "💎 Você está na lista de interesse VIP.\n\n"
            "Quando o acesso completo abrir, você será avisado por aqui."
        )

    elif normalized in ["/suporte", "suporte"]:
        send_message(
            chat_id,
            "💬 Me envie sua dúvida aqui no chat que eu te respondo."
        )

    elif normalized in ["/termos", "termos"]:
        handle_callback(chat_id, None, "terms")

    else:
        send_message(
            chat_id,
            "Recebi sua mensagem ✅\n\nPara acessar o menu principal, toque em /start."
        )


@app.post(f"/webhook/{WEBHOOK_SECRET}")
def telegram_webhook():
    update = request.get_json(silent=True) or {}

    if "callback_query" in update:
        callback = update["callback_query"]
        chat_id = callback["message"]["chat"]["id"]
        callback_id = callback["id"]
        data = callback.get("data", "")

        handle_callback(chat_id, callback_id, data)
        return {"ok": True}

    message = update.get("message") or update.get("edited_message")

    if not message:
        return {"ok": True}

    chat_id = message["chat"]["id"]
    text = message.get("text") or ""

    handle_text_message(chat_id, text)

    return {"ok": True}


@app.post("/asaas/webhook")
def asaas_webhook():
    token = request.headers.get("asaas-access-token", "")

    if ASAAS_WEBHOOK_TOKEN and token != ASAAS_WEBHOOK_TOKEN:
        return {"ok": False, "error": "invalid token"}, 403

    event = request.get_json(silent=True) or {}
    event_id = event.get("id")

    if event_id and event_id in PROCESSED_EVENTS:
        return {"ok": True, "duplicate": True}

    if event_id:
        PROCESSED_EVENTS.add(event_id)

    event_name = event.get("event", "")
    payment = event.get("payment") or {}
    payment_id = payment.get("id")
    status = payment.get("status", "")
    external_reference = payment.get("externalReference", "")

    if event_name in ["PAYMENT_CONFIRMED", "PAYMENT_RECEIVED"] or status in PAID_STATUSES:
        chat_id = None

        if payment_id in ORDERS:
            chat_id = ORDERS[payment_id]["chat_id"]

        if not chat_id:
            chat_id = parse_chat_id_from_external_reference(external_reference)

        if chat_id:
            deliver_pack(chat_id, payment_id)

    return {"ok": True}
