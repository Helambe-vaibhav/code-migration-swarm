# Legacy Payment Service - Synchronous business logic and external calls
import time
from models import Account, PaymentRecord
import database

def process_transfer(sender_id, recipient_id, amount):
    # Synchronous processing
    time.sleep(0.02)
    if amount <= 0:
        return {"success": False, "error": "Invalid amount"}

    sender = database.find_account(sender_id)
    if not sender:
        return {"success": False, "error": "Sender not found"}

    if sender.balance < amount:
        return {"success": False, "error": "Insufficient funds"}

    recipient = database.find_account(recipient_id)
    if not recipient:
        return {"success": False, "error": "Recipient not found"}

    sender.balance -= amount
    recipient.balance += amount

    database.save_account(sender)
    database.save_account(recipient)

    payment_id = "pay_%d" % int(time.time() * 1000)
    record = PaymentRecord(payment_id, sender_id, recipient_id, amount, status="COMPLETED")
    return {"success": True, "payment": record.to_dict()}
