import os


def get_authorized_chats() -> set[str]:
    raw = os.environ.get("TELEGRAM_AUTHORIZED_CHATS", "")
    if raw:
        return {cid.strip() for cid in raw.split(",") if cid.strip()}
    single = os.environ.get("TELEGRAM_CHAT_ID", "")
    return {single} if single else set()


def is_authorized_chat(chat_id: str | int) -> bool:
    return str(chat_id) in get_authorized_chats()
