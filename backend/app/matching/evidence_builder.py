from pathlib import Path

import pandas as pd


# ============================================================
# PATHS
# ============================================================

BASE_DIR = Path(__file__).resolve().parents[2]

RAW_DATA_DIR = BASE_DIR / "data" / "raw"
PROCESSED_DATA_DIR = BASE_DIR / "data" / "processed"


# ============================================================
# FILES
# ============================================================

GATEWAY_FILE = (
    RAW_DATA_DIR / "gateway_transactions.csv"
)

BANK_FILE = (
    RAW_DATA_DIR / "bank_statements.csv"
)

ORDERS_FILE = (
    RAW_DATA_DIR / "orders.csv"
)

EXCEPTIONS_FILE = (
    PROCESSED_DATA_DIR / "exceptions.csv"
)

FUZZY_FILE = (
    PROCESSED_DATA_DIR / "pass2_fuzzy_results.csv"
)


# ============================================================
# LOAD DATA
# ============================================================

def load_data():

    gateway = pd.read_csv(
        GATEWAY_FILE
    )

    bank = pd.read_csv(
        BANK_FILE
    )

    orders = pd.read_csv(
        ORDERS_FILE
    )

    exceptions = pd.read_csv(
        EXCEPTIONS_FILE
    )

    fuzzy = pd.read_csv(
        FUZZY_FILE
    )

    return (
        gateway,
        bank,
        orders,
        exceptions,
        fuzzy,
    )


# ============================================================
# SAFE VALUE
# ============================================================

def safe_value(
    value,
    default=None,
):
    """
    Convert NaN values into safe Python values.
    """

    if pd.isna(value):
        return default

    return value


# ============================================================
# FIND GATEWAY TRANSACTION
# ============================================================

def find_gateway_transaction(
    transaction_id,
    gateway,
):
    """
    Retrieve the gateway transaction.
    """

    matches = gateway[
        gateway[
            "gateway_transaction_id"
        ].astype(str)
        == str(transaction_id)
    ]

    if matches.empty:
        return None

    return matches.iloc[0]


# ============================================================
# FIND ORDER
# ============================================================

def find_order(
    transaction_id,
    gateway_row,
    orders,
):
    """
    Find the corresponding internal order.
    """

    if gateway_row is None:
        return None

    order_reference = safe_value(
        gateway_row.get(
            "order_reference"
        )
    )

    if order_reference is None:
        return None

    matches = orders[
        orders[
            "order_id"
        ].astype(str)
        == str(order_reference)
    ]

    if matches.empty:
        return None

    return matches.iloc[0]


# ============================================================
# FIND BANK CANDIDATE
# ============================================================

def find_bank_candidate(
    bank_reference,
    bank,
):
    """
    Retrieve the selected bank settlement.
    """

    if (
        bank_reference is None
        or pd.isna(bank_reference)
    ):
        return None

    matches = bank[
        bank[
            "bank_reference"
        ].astype(str)
        == str(bank_reference)
    ]

    if matches.empty:
        return None

    return matches.iloc[0]


# ============================================================
# FIND FUZZY RESULT
# ============================================================

def find_fuzzy_result(
    transaction_id,
    fuzzy,
):
    """
    Retrieve the fuzzy matching evidence.
    """

    matches = fuzzy[
        fuzzy[
            "gateway_transaction_id"
        ].astype(str)
        == str(transaction_id)
    ]

    if matches.empty:
        return None

    return matches.iloc[0]


# ============================================================
# BUILD GATEWAY EVIDENCE
# ============================================================

def build_gateway_evidence(
    gateway_row,
):
    """
    Convert gateway record into a compact evidence object.
    """

    if gateway_row is None:
        return None

    return {
        "transaction_id":
            safe_value(
                gateway_row.get(
                    "gateway_transaction_id"
                )
            ),

        "order_reference":
            safe_value(
                gateway_row.get(
                    "order_reference"
                )
            ),

        "merchant":
            safe_value(
                gateway_row.get(
                    "merchant_name"
                )
            ),

        "amount":
            safe_value(
                gateway_row.get(
                    "amount"
                )
            ),

        "currency":
            safe_value(
                gateway_row.get(
                    "currency"
                )
            ),

        "transaction_date":
            safe_value(
                gateway_row.get(
                    "transaction_date"
                )
            ),

        "payment_status":
            safe_value(
                gateway_row.get(
                    "payment_status"
                )
            ),
    }


# ============================================================
# BUILD ORDER EVIDENCE
# ============================================================

def build_order_evidence(
    order_row,
):
    """
    Convert internal order record into evidence.
    """

    if order_row is None:
        return None

    return {
        "order_id":
            safe_value(
                order_row.get(
                    "order_id"
                )
            ),

        "customer":
            safe_value(
                order_row.get(
                    "customer_name"
                )
            ),

        "merchant":
            safe_value(
                order_row.get(
                    "merchant_name"
                )
            ),

        "amount":
            safe_value(
                order_row.get(
                    "amount"
                )
            ),

        "currency":
            safe_value(
                order_row.get(
                    "currency"
                )
            ),

        "order_date":
            safe_value(
                order_row.get(
                    "order_date"
                )
            ),

        "payment_status":
            safe_value(
                order_row.get(
                    "payment_status"
                )
            ),
    }


# ============================================================
# BUILD BANK EVIDENCE
# ============================================================

def build_bank_evidence(
    bank_row,
):
    """
    Convert bank settlement into evidence.
    """

    if bank_row is None:
        return None

    return {
        "bank_reference":
            safe_value(
                bank_row.get(
                    "bank_reference"
                )
            ),

        "transaction_reference":
            safe_value(
                bank_row.get(
                    "transaction_reference"
                )
            ),

        "merchant":
            safe_value(
                bank_row.get(
                    "merchant_name"
                )
            ),

        "settlement_amount":
            safe_value(
                bank_row.get(
                    "credit_amount"
                )
            ),

        "currency":
            safe_value(
                bank_row.get(
                    "currency"
                )
            ),

        "settlement_date":
            safe_value(
                bank_row.get(
                    "settlement_date"
                )
            ),

        "transaction_type":
            safe_value(
                bank_row.get(
                    "transaction_type"
                )
            ),
    }


# ============================================================
# BUILD MATCHING EVIDENCE
# ============================================================

def build_matching_evidence(
    fuzzy_row,
):
    """
    Extract matching-engine evidence.
    """

    if fuzzy_row is None:
        return None

    return {
        "method":
            safe_value(
                fuzzy_row.get(
                    "fuzzy_method"
                )
            ),

        "confidence":
            safe_value(
                fuzzy_row.get(
                    "fuzzy_confidence"
                )
            ),

        "reference_similarity":
            safe_value(
                fuzzy_row.get(
                    "reference_similarity"
                )
            ),

        "merchant_similarity":
            safe_value(
                fuzzy_row.get(
                    "merchant_similarity"
                )
            ),

        "amount_similarity":
            safe_value(
                fuzzy_row.get(
                    "amount_similarity"
                )
            ),

        "date_similarity":
            safe_value(
                fuzzy_row.get(
                    "date_similarity"
                )
            ),

        "amount_difference":
            safe_value(
                fuzzy_row.get(
                    "amount_difference"
                )
            ),

        "candidate_count":
            safe_value(
                fuzzy_row.get(
                    "candidate_count"
                )
            ),

        "second_best_score":
            safe_value(
                fuzzy_row.get(
                    "second_best_score"
                )
            ),

        "score_gap":
            safe_value(
                fuzzy_row.get(
                    "score_gap"
                )
            ),

        "reason":
            safe_value(
                fuzzy_row.get(
                    "reason"
                )
            ),

        "recommended_action":
            safe_value(
                fuzzy_row.get(
                    "recommended_action"
                )
            ),
    }


# ============================================================
# BUILD EXCEPTION EVIDENCE
# ============================================================

def build_exception_evidence(
    exception_row,
):
    """
    Extract exception classification evidence.
    """

    return {
        "exception_type":
            safe_value(
                exception_row.get(
                    "exception_type"
                )
            ),

        "severity":
            safe_value(
                exception_row.get(
                    "severity"
                )
            ),

        "confidence":
            safe_value(
                exception_row.get(
                    "confidence"
                )
            ),

        "amount_at_risk":
            safe_value(
                exception_row.get(
                    "amount_at_risk"
                )
            ),

        "amount_difference":
            safe_value(
                exception_row.get(
                    "amount_difference"
                )
            ),

        "explanation":
            safe_value(
                exception_row.get(
                    "explanation"
                )
            ),

        "recommended_action":
            safe_value(
                exception_row.get(
                    "recommended_action"
                )
            ),
    }


# ============================================================
# BUILD COMPLETE EVIDENCE PACKAGE
# ============================================================

def build_evidence_package(
    transaction_id,
    gateway,
    bank,
    orders,
    exceptions,
    fuzzy,
):
    """
    Construct a complete evidence package for one exception.

    This object is what we will eventually send to the LLM.
    """

    transaction_id = str(
        transaction_id
    )

    # --------------------------------------------------------
    # Exception
    # --------------------------------------------------------

    exception_matches = exceptions[
        exceptions[
            "transaction_id"
        ].astype(str)
        == transaction_id
    ]

    if exception_matches.empty:
        return None

    exception_row = (
        exception_matches.iloc[0]
    )

    # --------------------------------------------------------
    # Gateway
    # --------------------------------------------------------

    gateway_row = (
        find_gateway_transaction(
            transaction_id,
            gateway,
        )
    )

    # --------------------------------------------------------
    # Order
    # --------------------------------------------------------

    order_row = (
        find_order(
            transaction_id,
            gateway_row,
            orders,
        )
    )

    # --------------------------------------------------------
    # Bank
    # --------------------------------------------------------

    bank_reference = safe_value(
        exception_row.get(
            "bank_reference"
        )
    )

    bank_row = (
        find_bank_candidate(
            bank_reference,
            bank,
        )
    )

    # --------------------------------------------------------
    # Fuzzy
    # --------------------------------------------------------

    fuzzy_row = (
        find_fuzzy_result(
            transaction_id,
            fuzzy,
        )
    )

    # --------------------------------------------------------
    # Package
    # --------------------------------------------------------

    package = {
        "transaction_id":
            transaction_id,

        "exception":
            build_exception_evidence(
                exception_row
            ),

        "gateway":
            build_gateway_evidence(
                gateway_row
            ),

        "order":
            build_order_evidence(
                order_row
            ),

        "bank":
            build_bank_evidence(
                bank_row
            ),

        "matching":
            build_matching_evidence(
                fuzzy_row
            ),
    }

    return package


# ============================================================
# BUILD ALL EVIDENCE
# ============================================================

def build_all_evidence(
    gateway,
    bank,
    orders,
    exceptions,
    fuzzy,
):
    """
    Build evidence packages for all exceptions.
    """

    packages = []

    for transaction_id in (
        exceptions[
            "transaction_id"
        ].dropna().unique()
    ):

        package = (
            build_evidence_package(
                transaction_id,
                gateway,
                bank,
                orders,
                exceptions,
                fuzzy,
            )
        )

        if package is not None:

            packages.append(
                package
            )

    return packages


# ============================================================
# MAIN
# ============================================================

def main():

    print("=" * 60)
    print(
        "ReconcileAI — Evidence Builder"
    )
    print("=" * 60)

    # --------------------------------------------------------
    # Check files
    # --------------------------------------------------------

    required_files = [
        GATEWAY_FILE,
        BANK_FILE,
        ORDERS_FILE,
        EXCEPTIONS_FILE,
        FUZZY_FILE,
    ]

    for file in required_files:

        if not file.exists():

            raise FileNotFoundError(
                f"Required file not found:\n{file}"
            )

    # --------------------------------------------------------
    # Load
    # --------------------------------------------------------

    (
        gateway,
        bank,
        orders,
        exceptions,
        fuzzy,
    ) = load_data()

    print(
        f"\nGateway records: "
        f"{len(gateway)}"
    )

    print(
        f"Bank records: "
        f"{len(bank)}"
    )

    print(
        f"Order records: "
        f"{len(orders)}"
    )

    print(
        f"Exceptions: "
        f"{len(exceptions)}"
    )

    # --------------------------------------------------------
    # Build
    # --------------------------------------------------------

    print(
        "\nBuilding evidence packages..."
    )

    packages = build_all_evidence(
        gateway,
        bank,
        orders,
        exceptions,
        fuzzy,
    )

    print(
        f"Evidence packages created: "
        f"{len(packages)}"
    )

    # --------------------------------------------------------
    # Save JSON
    # --------------------------------------------------------

    import json

    output_file = (
        PROCESSED_DATA_DIR
        / "evidence_packages.json"
    )

    with open(
        output_file,
        "w",
        encoding="utf-8",
    ) as file:

        json.dump(
            packages,
            file,
            indent=2,
            ensure_ascii=False,
            default=str,
        )

    print(
        f"\nEvidence packages saved to:"
        f"\n{output_file}"
    )

    # --------------------------------------------------------
    # Example
    # --------------------------------------------------------

    if packages:

        print(
            "\nEXAMPLE EVIDENCE PACKAGE"
        )

        print("-" * 60)

        print(
            json.dumps(
                packages[0],
                indent=2,
                ensure_ascii=False,
                default=str,
            )
        )

    print(
        "\nEvidence building complete."
    )


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":
    main()