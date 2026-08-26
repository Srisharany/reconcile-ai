from pathlib import Path

import pandas as pd


# ============================================================
# PATHS
# ============================================================

BASE_DIR = Path(__file__).resolve().parents[2]

RAW_DATA_DIR = BASE_DIR / "data" / "raw"


# ============================================================
# LOAD DATA
# ============================================================

def load_data():
    """
    Load the three source datasets.

    Returns:
        orders
        gateway
        bank
    """

    orders = pd.read_csv(
        RAW_DATA_DIR / "orders.csv"
    )

    gateway = pd.read_csv(
        RAW_DATA_DIR / "gateway_transactions.csv"
    )

    bank = pd.read_csv(
        RAW_DATA_DIR / "bank_statements.csv"
    )

    return orders, gateway, bank


# ============================================================
# NORMALIZATION
# ============================================================

def normalize_text(value):
    """
    Normalize text so small formatting differences
    don't immediately prevent matching.
    """

    if pd.isna(value):
        return ""

    return (
        str(value)
        .strip()
        .upper()
        .replace("-", "")
        .replace("_", "")
        .replace(" ", "")
    )


def normalize_data(
    orders: pd.DataFrame,
    gateway: pd.DataFrame,
    bank: pd.DataFrame,
):
    """
    Create normalized columns without modifying
    the original source columns.
    """

    orders = orders.copy()
    gateway = gateway.copy()
    bank = bank.copy()

    # --------------------------------------------------------
    # Orders
    # --------------------------------------------------------

    orders["order_id_normalized"] = (
        orders["order_id"]
        .apply(normalize_text)
    )

    orders["merchant_normalized"] = (
        orders["merchant_name"]
        .apply(normalize_text)
    )

    orders["amount_normalized"] = (
        orders["amount"]
        .round(2)
    )

    # --------------------------------------------------------
    # Gateway
    # --------------------------------------------------------

    gateway["gateway_id_normalized"] = (
        gateway["gateway_transaction_id"]
        .apply(normalize_text)
    )

    gateway["order_reference_normalized"] = (
        gateway["order_reference"]
        .apply(normalize_text)
    )

    gateway["merchant_normalized"] = (
        gateway["merchant_name"]
        .apply(normalize_text)
    )

    gateway["amount_normalized"] = (
        gateway["amount"]
        .round(2)
    )

    # --------------------------------------------------------
    # Bank
    # --------------------------------------------------------

    bank["transaction_reference_normalized"] = (
        bank["transaction_reference"]
        .apply(normalize_text)
    )

    bank["bank_reference_normalized"] = (
        bank["bank_reference"]
        .apply(normalize_text)
    )

    bank["merchant_normalized"] = (
        bank["merchant_name"]
        .apply(normalize_text)
    )

    bank["amount_normalized"] = (
        bank["credit_amount"]
        .round(2)
    )

    return orders, gateway, bank


# ============================================================
# PASS 1 — EXACT ORDER ↔ GATEWAY MATCHING
# ============================================================

def match_orders_to_gateway(
    orders: pd.DataFrame,
    gateway: pd.DataFrame,
):
    """
    Match internal orders with payment gateway transactions
    using exact order references and amount.
    """

    results = []

    for _, order in orders.iterrows():

        candidates = gateway[
            gateway["order_reference_normalized"]
            == order["order_id_normalized"]
        ]

        if candidates.empty:

            results.append(
                {
                    "order_id": order["order_id"],
                    "gateway_transaction_id": None,
                    "order_gateway_status": "UNMATCHED",
                    "order_gateway_method": None,
                    "order_gateway_confidence": 0.0,
                }
            )

            continue

        # Find candidates with exact amount.
        exact_amount = candidates[
            candidates["amount_normalized"]
            == order["amount_normalized"]
        ]

        if len(exact_amount) == 1:

            gateway_record = exact_amount.iloc[0]

            results.append(
                {
                    "order_id": order["order_id"],
                    "gateway_transaction_id": (
                        gateway_record[
                            "gateway_transaction_id"
                        ]
                    ),
                    "order_gateway_status": "MATCHED",
                    "order_gateway_method": "EXACT",
                    "order_gateway_confidence": 1.0,
                }
            )

        elif len(exact_amount) > 1:

            # Multiple identical gateway records.
            results.append(
                {
                    "order_id": order["order_id"],
                    "gateway_transaction_id": None,
                    "order_gateway_status": "REVIEW",
                    "order_gateway_method": "EXACT_DUPLICATE",
                    "order_gateway_confidence": 0.5,
                }
            )

        else:

            # Order reference exists but amount differs.
            gateway_record = candidates.iloc[0]

            results.append(
                {
                    "order_id": order["order_id"],
                    "gateway_transaction_id": (
                        gateway_record[
                            "gateway_transaction_id"
                        ]
                    ),
                    "order_gateway_status": "EXCEPTION",
                    "order_gateway_method": "REFERENCE_AMOUNT_MISMATCH",
                    "order_gateway_confidence": 0.4,
                }
            )

    return pd.DataFrame(results)


# ============================================================
# PASS 1 — GATEWAY ↔ BANK EXACT MATCHING
# ============================================================

def match_gateway_to_bank(
    gateway: pd.DataFrame,
    bank: pd.DataFrame,
):
    """
    Match gateway transactions with bank settlements.

    Primary exact key:
        gateway transaction ID
        ↔
        bank transaction reference

    Amount is also verified.
    """

    results = []

    for _, transaction in gateway.iterrows():

        candidates = bank[
            bank["transaction_reference_normalized"]
            == transaction["gateway_id_normalized"]
        ]

        if candidates.empty:

            results.append(
                {
                    "gateway_transaction_id": (
                        transaction[
                            "gateway_transaction_id"
                        ]
                    ),
                    "bank_reference": None,
                    "gateway_bank_status": "UNMATCHED",
                    "gateway_bank_method": None,
                    "gateway_bank_confidence": 0.0,
                }
            )

            continue

        exact_amount = candidates[
            candidates["amount_normalized"]
            == transaction["amount_normalized"]
        ]

        if len(exact_amount) == 1:

            bank_record = exact_amount.iloc[0]

            results.append(
                {
                    "gateway_transaction_id": (
                        transaction[
                            "gateway_transaction_id"
                        ]
                    ),
                    "bank_reference": (
                        bank_record[
                            "bank_reference"
                        ]
                    ),
                    "gateway_bank_status": "MATCHED",
                    "gateway_bank_method": "EXACT",
                    "gateway_bank_confidence": 1.0,
                }
            )

        elif len(exact_amount) > 1:

            results.append(
                {
                    "gateway_transaction_id": (
                        transaction[
                            "gateway_transaction_id"
                        ]
                    ),
                    "bank_reference": None,
                    "gateway_bank_status": "REVIEW",
                    "gateway_bank_method": "EXACT_DUPLICATE",
                    "gateway_bank_confidence": 0.5,
                }
            )

        else:

            bank_record = candidates.iloc[0]

            results.append(
                {
                    "gateway_transaction_id": (
                        transaction[
                            "gateway_transaction_id"
                        ]
                    ),
                    "bank_reference": (
                        bank_record[
                            "bank_reference"
                        ]
                    ),
                    "gateway_bank_status": "EXCEPTION",
                    "gateway_bank_method": "REFERENCE_AMOUNT_MISMATCH",
                    "gateway_bank_confidence": 0.4,
                }
            )

    return pd.DataFrame(results)


# ============================================================
# BUILD COMPLETE RECONCILIATION RESULT
# ============================================================

def build_reconciliation_results(
    orders: pd.DataFrame,
    gateway: pd.DataFrame,
    bank: pd.DataFrame,
):
    """
    Build the first version of the complete reconciliation
    result using exact matching only.
    """

    order_gateway = match_orders_to_gateway(
        orders,
        gateway,
    )

    gateway_bank = match_gateway_to_bank(
        gateway,
        bank,
    )

    results = order_gateway.merge(
        gateway_bank,
        on="gateway_transaction_id",
        how="left",
    )

    return results


# ============================================================
# SUMMARY
# ============================================================

def print_summary(results: pd.DataFrame):
    """
    Print reconciliation statistics.
    """

    print("\n" + "=" * 60)
    print("RECONCILIATION SUMMARY")
    print("=" * 60)

    print(
        f"\nTotal orders: "
        f"{len(results)}"
    )

    print("\nOrder → Gateway")

    print(
        results[
            "order_gateway_status"
        ].value_counts()
        .to_string()
    )

    print("\nGateway → Bank")

    print(
        results[
            "gateway_bank_status"
        ].value_counts()
        .to_string()
    )

    exact_order_gateway = (
        results["order_gateway_status"]
        == "MATCHED"
    ).sum()

    exact_gateway_bank = (
        results["gateway_bank_status"]
        == "MATCHED"
    ).sum()

    print(
        f"\nExact Order → Gateway matches: "
        f"{exact_order_gateway}"
    )

    print(
        f"Exact Gateway → Bank matches: "
        f"{exact_gateway_bank}"
    )


# ============================================================
# MAIN
# ============================================================

def main():

    print("=" * 60)
    print("ReconcileAI — Pass 1: Exact Matching")
    print("=" * 60)

    print("\nLoading datasets...")

    orders, gateway, bank = load_data()

    print(
        f"Orders:   {len(orders)}"
    )

    print(
        f"Gateway:  {len(gateway)}"
    )

    print(
        f"Bank:     {len(bank)}"
    )

    print("\nNormalizing data...")

    orders, gateway, bank = normalize_data(
        orders,
        gateway,
        bank,
    )

    print("Normalization complete.")

    print("\nRunning exact matching...")

    results = build_reconciliation_results(
        orders,
        gateway,
        bank,
    )

    print_summary(results)

    # --------------------------------------------------------
    # Save results
    # --------------------------------------------------------

    output_dir = (
        BASE_DIR
        / "data"
        / "processed"
    )

    output_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    output_file = (
        output_dir
        / "exact_reconciliation_results.csv"
    )

    results.to_csv(
        output_file,
        index=False,
    )

    print(
        f"\nResults saved to:\n"
        f"{output_file}"
    )

    print("\nPass 1 complete.")


if __name__ == "__main__":
    main()