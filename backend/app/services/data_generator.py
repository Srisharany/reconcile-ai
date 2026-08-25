import random
import uuid
from datetime import date, datetime, timedelta

import pandas as pd
from faker import Faker


fake = Faker("en_IN")


MERCHANTS = [
    "Sri Lakshmi Stores",
    "ABC Electronics",
    "Fresh Mart",
    "Urban Fashion",
    "Tech World",
    "Green Grocery",
    "Smart Home",
    "Daily Needs",
]


def generate_base_transactions(count: int = 1000):
    """
    Generate clean master transactions.

    This master dataset represents the ground truth before
    any corruption or inconsistencies are introduced.
    """

    transactions = []

    start_date = datetime(2026, 8, 1)

    for i in range(1, count + 1):
        transaction_id = f"TXN{i:06d}"
        order_id = f"ORD{i:06d}"

        amount = round(random.uniform(100, 25000), 2)

        merchant = random.choice(MERCHANTS)

        transaction_date = start_date + timedelta(
            days=random.randint(0, 20)
        )

        transactions.append(
            {
                "transaction_id": transaction_id,
                "order_id": order_id,
                "customer_name": fake.name(),
                "merchant_name": merchant,
                "amount": amount,
                "currency": "INR",
                "transaction_date": transaction_date.date(),
            }
        )

    return transactions


def create_orders(master):
    """
    Create internal order records from the master transactions.
    """

    orders = []

    for tx in master:
        orders.append(
            {
                "order_id": tx["order_id"],
                "customer_name": tx["customer_name"],
                "merchant_name": tx["merchant_name"],
                "amount": tx["amount"],
                "currency": tx["currency"],
                "order_date": tx["transaction_date"],
                "payment_status": "PAID",
            }
        )

    return pd.DataFrame(orders)


def create_gateway_transactions(master):
    """
    Create payment gateway transaction records.
    """

    gateway = []

    for tx in master:
        gateway.append(
            {
                "gateway_transaction_id": tx["transaction_id"],
                "order_reference": tx["order_id"],
                "merchant_name": tx["merchant_name"],
                "amount": tx["amount"],
                "currency": tx["currency"],
                "transaction_date": tx["transaction_date"],
                "payment_status": "SUCCESS",
            }
        )

    return pd.DataFrame(gateway)


def create_bank_statements(master):
    """
    Create bank settlement records.

    Settlement can happen 0-2 days after the original
    transaction date.
    """

    bank = []

    for tx in master:
        settlement_date = tx["transaction_date"] + timedelta(
            days=random.randint(0, 2)
        )

        bank.append(
            {
                "bank_reference": (
                    f"BANK-{uuid.uuid4().hex[:8].upper()}"
                ),
                "transaction_reference": tx["transaction_id"],
                "merchant_name": tx["merchant_name"],
                "credit_amount": tx["amount"],
                "currency": tx["currency"],
                "settlement_date": settlement_date,
                "transaction_type": "CREDIT",
            }
        )

    return pd.DataFrame(bank)


def generate_dataset(count: int = 1000):
    """
    Generate all three clean source datasets.

    Returns:
        orders: Internal order records
        gateway: Payment gateway records
        bank: Bank settlement records
    """

    master = generate_base_transactions(count)

    orders = create_orders(master)
    gateway = create_gateway_transactions(master)
    bank = create_bank_statements(master)

    return orders, gateway, bank


if __name__ == "__main__":
    orders, gateway, bank = generate_dataset(1000)

    print(f"Orders: {len(orders)}")
    print(f"Gateway transactions: {len(gateway)}")
    print(f"Bank statements: {len(bank)}")