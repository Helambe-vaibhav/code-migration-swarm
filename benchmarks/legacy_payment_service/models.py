# Legacy Models - Untyped Python 3.6 style

class Account:
    def __init__(self, account_id, balance=0.0, currency="USD"):
        self.account_id = account_id
        self.balance = float(balance)
        self.currency = currency
        self.transactions = []

    def to_dict(self):
        return {
            "account_id": self.account_id,
            "balance": self.balance,
            "currency": self.currency,
            "transactions": self.transactions
        }


class PaymentRecord:
    def __init__(self, payment_id, sender_id, recipient_id, amount, status="PENDING"):
        self.payment_id = payment_id
        self.sender_id = sender_id
        self.recipient_id = recipient_id
        self.amount = float(amount)
        self.status = status

    def to_dict(self):
        return {
            "payment_id": self.payment_id,
            "sender_id": self.sender_id,
            "recipient_id": self.recipient_id,
            "amount": self.amount,
            "status": self.status
        }
