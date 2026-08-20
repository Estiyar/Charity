from .redistribution import handle_card_status_changed
from .suspend_handlers import handle_card_suspended


EVENT_HANDLERS = {
    "card.status_changed": handle_card_status_changed,
    "card.suspended": handle_card_suspended,
}
