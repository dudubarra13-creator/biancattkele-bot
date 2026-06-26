import os
import requests
from flask import Flask, request

app = Flask(__name__)

BOT_TOKEN = os.environ.get("BOT_TOKEN")
WEBHOOK_SECRET = os.environ.get("WEBHOOK_SECRET", "biancattkele123")

TELEGRAM_API = f"https://api.telegram.org/bot{BOT_TOKEN}"


def telegram(method, payload):
    try:
        response = requests.post(
            f"{TELEGRAM_API}/{method}",
            json=payload,
            timeout=15
        )
        return response.json()
    except Exception as error:
        print("Telegram error:", error)
        return None


def send_message(chat_id, text, keyboard=None):
    payload = {
        "chat_id": chat_id,
        "text": text
    }

    if keyboard:
        payload["reply_markup"] = {
            "inline_keyboard": keyboard
        }

    return telegram("sendMessage", payload)


def answer_callback(callback_id):
    return telegram("answerCallbackQuery", {
        "callback_query_id": callback_id
    })


def age_gate_keyboard():
    return [
        [{"text": "✅ Tenho 18+ e quero entrar", "callback_data": "confirm_18"}],
        [{"text": "❌ Sair", "callback_data": "exit"}]
    ]


def main_menu_keyboard():
    return [
        [{"text": "👀 Ver fotos disponíveis", "callback_data": "see_photos"}],
        [{"text": "💋 Liberar acesso às 12 fotos", "callback_data": "buy_pack"}],
        [{"text": "💎 Lista VIP", "callback_data": "vip_list"}],
        [{"text": "📜 Termos do acesso", "callback_data": "terms"}],
        [{"text": "💬 Suporte", "callback_data": "support"}]
    ]


def buy_keyboard():
    return [
        [{"text": "✅ Quero gerar meu Pix", "callback_data": "generate_pix"}],
        [{"text": "⬅️ Voltar", "callback_data": "back_menu"}]
    ]


def back_keyboard():
    return [
        [{"text": "⬅️ Voltar ao menu", "callback_data": "back_menu"}]
    ]


@app.get("/")
def home():
    return "Bot Bianca Monteiro online ✅"


def send_start(chat_id):
    text = (
        "💋 Você chegou no lado mais reservado da Bianca Monteiro.\n\n"
        "Antes de continuar, preciso confirmar uma coisa:\n\n"
        "Este acesso é exclusivo para maiores de 18 anos e contém fotos "
        "sensuais, íntimas e reservadas, sem nudez explícita.\n\n"
        "Se você tem 18 anos ou mais, toque no botão abaixo para continuar 🔞"
    )

    send_message(chat_id, text, age_gate_keyboard())


def send_main_menu(chat_id):
    text = (
        "Acesso liberado 💋\n\n"
        "A Bianca separou fotos que não aparecem nas redes, com uma estética "
        "mais íntima, sensual e exclusiva.\n\n"
        "Escolha uma opção abaixo:"
    )

    send_message(chat_id, text, main_menu_keyboard())


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
        text = (
            "👀 O que você encontra aqui:\n\n"
            "• 12 fotos sensuais da Bianca Monteiro\n"
            "• clima íntimo, elegante e reservado\n"
            "• conteúdo adulto, sem nudez explícita\n"
            "• entrega após confirmação do acesso\n\n"
            "É aquele tipo de foto que fica fora das redes sociais. "
            "Mais privada, mais próxima, mais Bianca. 💋"
        )

        send_message(chat_id, text, [
            [{"text": "💋 Quero liberar as 12 fotos", "callback_data": "buy_pack"}],
            [{"text": "⬅️ Voltar", "callback_data": "back_menu"}]
        ])

    elif data == "buy_pack":
        text = (
            "💋 Acesso às 12 fotos reservadas da Bianca\n\n"
            "Você recebe:\n"
            "• 12 fotos sensuais e exclusivas\n"
            "• entrega pelo Telegram\n"
            "• acesso discreto e direto\n\n"
            "Valor de teste:\n"
            "R$ 14,90\n\n"
            "Toque abaixo para continuar."
        )

        send_message(chat_id, text, buy_keyboard())

    elif data == "generate_pix":
        text = (
            "Perfeito 💋\n\n"
            "A próxima etapa é conectar o Pix automático pela Asaas.\n\n"
            "Quando a integração estiver ligada, este botão vai gerar o Pix "
            "Copia e Cola e liberar as fotos automaticamente após confirmação."
        )

        send_message(chat_id, text, back_keyboard())

    elif data == "vip_list":
        text = (
            "💎 Lista VIP Bianca\n\n"
            "O VIP completo ainda não abriu.\n\n"
            "Mas quem entrar na lista vai receber aviso antes, condições de lançamento "
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


@app.post(f"/webhook/{WEBHOOK_SECRET}")
def webhook():
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
    text = (message.get("text") or "").strip().lower()

    if text in ["/start", "start", "começar"]:
        send_start(chat_id)

    elif text in ["/pack", "pack", "fotos"]:
        send_main_menu(chat_id)

    elif text in ["/vip", "quero vip"]:
        send_message(
            chat_id,
            "💎 Você está na lista de interesse VIP.\n\nQuando o acesso completo abrir, você será avisado por aqui."
        )

    elif text in ["/suporte", "suporte"]:
        send_message(
            chat_id,
            "💬 Me envie sua dúvida aqui no chat que eu te respondo."
        )

    elif text in ["/termos", "termos"]:
        handle_callback(chat_id, "0", "terms")

    else:
        send_message(
            chat_id,
            "Recebi sua mensagem ✅\n\nPara acessar o menu principal, toque em /start."
        )

    return {"ok": True}
