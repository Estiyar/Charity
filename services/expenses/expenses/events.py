from .ledger_services import record_donation_credit, record_redistribution


def on_payment_succeeded(payload):
    record_donation_credit(payload)


def on_redistribution_choice(payload):
    record_redistribution(payload)


EVENT_HANDLERS = {
    "payment.succeeded": on_payment_succeeded,
    "redistribution.choice_applied": on_redistribution_choice,
}
