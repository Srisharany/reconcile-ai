from pathlib import Path

import pandas as pd


# ============================================================
# PATHS
# ============================================================

BASE_DIR = Path(__file__).resolve().parents[2]

PROCESSED_DATA_DIR = (
    BASE_DIR / "data" / "processed"
)


# ============================================================
# CONFIGURATION
# ============================================================

# Amount difference above this is considered a significant
# mismatch rather than a small possible fee.
SIGNIFICANT_AMOUNT_THRESHOLD = 100.00

# High-value exceptions.
HIGH_VALUE_THRESHOLD = 10000.00

# Medium-value exceptions.
MEDIUM_VALUE_THRESHOLD = 1000.00


# ============================================================
# SEVERITY
# ============================================================

def calculate_severity(
    exception_type,
    amount_at_risk,
    confidence,
):
    """
    Calculate operational severity.

    CRITICAL:
        Large financial exposure or duplicate.

    HIGH:
        Significant amount mismatch or missing settlement.

    MEDIUM:
        Ambiguous/review cases or possible fees.

    LOW:
        Minor / low-confidence exceptions.
    """

    try:
        amount = float(
            amount_at_risk
            if amount_at_risk is not None
            else 0
        )
    except (TypeError, ValueError):
        amount = 0.0

    if exception_type == "DUPLICATE_TRANSACTION":
        return "CRITICAL"

    if exception_type == "MISSING_SETTLEMENT":

        if amount >= HIGH_VALUE_THRESHOLD:
            return "CRITICAL"

        return "HIGH"

    if exception_type == "AMOUNT_MISMATCH":

        if amount >= HIGH_VALUE_THRESHOLD:
            return "CRITICAL"

        if amount >= MEDIUM_VALUE_THRESHOLD:
            return "HIGH"

        return "MEDIUM"

    if exception_type == "AMBIGUOUS_MATCH":

        if amount >= HIGH_VALUE_THRESHOLD:
            return "HIGH"

        return "MEDIUM"

    if exception_type == "POSSIBLE_FEE":

        if amount >= MEDIUM_VALUE_THRESHOLD:
            return "HIGH"

        return "MEDIUM"

    if exception_type == "LOW_CONFIDENCE":

        return "LOW"

    return "MEDIUM"


# ============================================================
# EXCEPTION CLASSIFICATION
# ============================================================

def classify_exception(row):
    """
    Convert one reconciliation result into a structured
    finance exception.

    Returns None for transactions that are safely reconciled.
    """

    status = str(
        row.get(
            "reconciliation_status",
            ""
        )
    ).upper()

    confidence = row.get(
        "reconciliation_confidence",
        0.0,
    )

    amount_difference = row.get(
        "amount_difference",
        0.0,
    )

    # --------------------------------------------------------
    # Clean NaN values
    # --------------------------------------------------------

    if pd.isna(confidence):
        confidence = 0.0

    if pd.isna(amount_difference):
        amount_difference = 0.0

    try:
        confidence = float(confidence)
    except (TypeError, ValueError):
        confidence = 0.0

    try:
        amount_difference = float(
            amount_difference
        )
    except (TypeError, ValueError):
        amount_difference = 0.0

    # --------------------------------------------------------
    # Transaction amount
    # --------------------------------------------------------

    transaction_amount = row.get(
        "amount",
        row.get(
            "original_amount",
            0.0,
        ),
    )

    if pd.isna(transaction_amount):
        transaction_amount = 0.0

    try:
        transaction_amount = float(
            transaction_amount
        )
    except (TypeError, ValueError):
        transaction_amount = 0.0

    # ========================================================
    # MATCHED
    # ========================================================

    if status in {
        "MATCHED",
    }:

        return None

    # ========================================================
    # DUPLICATE
    # ========================================================

    if status == "DUPLICATE":

        return {
            "exception_type":
                "DUPLICATE_TRANSACTION",

            "severity":
                calculate_severity(
                    "DUPLICATE_TRANSACTION",
                    transaction_amount,
                    confidence,
                ),

            "confidence":
                round(confidence, 4),

            "amount_at_risk":
                round(
                    transaction_amount,
                    2,
                ),

            "explanation":
                (
                    "Multiple bank settlement "
                    "records appear to correspond "
                    "to the same transaction reference."
                ),

            "recommended_action":
                (
                    "Investigate duplicate settlement "
                    "records before reconciliation."
                ),
        }

    # ========================================================
    # MISSING SETTLEMENT
    # ========================================================

    if status in {
        "MISSING_SETTLEMENT",
        "UNRESOLVED",
    }:

        return {
            "exception_type":
                "MISSING_SETTLEMENT",

            "severity":
                calculate_severity(
                    "MISSING_SETTLEMENT",
                    transaction_amount,
                    confidence,
                ),

            "confidence":
                round(confidence, 4),

            "amount_at_risk":
                round(
                    transaction_amount,
                    2,
                ),

            "explanation":
                (
                    "No sufficiently reliable bank "
                    "settlement could be identified "
                    "for this gateway transaction."
                ),

            "recommended_action":
                (
                    "Check settlement files, settlement "
                    "timing and bank records."
                ),
        }

    # ========================================================
    # FEE
    # ========================================================

    if status == "MATCHED_WITH_FEE":

        return {
            "exception_type":
                "POSSIBLE_FEE",

            "severity":
                calculate_severity(
                    "POSSIBLE_FEE",
                    amount_difference,
                    confidence,
                ),

            "confidence":
                round(confidence, 4),

            "amount_at_risk":
                round(
                    amount_difference,
                    2,
                ),

            "explanation":
                (
                    f"The gateway and bank records "
                    f"appear to represent the same "
                    f"transaction, but the settlement "
                    f"amount differs by "
                    f"₹{amount_difference:.2f}. "
                    f"The difference may represent a "
                    f"gateway fee or settlement adjustment."
                ),

            "recommended_action":
                (
                    "Verify the applicable fee or "
                    "settlement adjustment."
                ),
        }

    # ========================================================
    # AMOUNT MISMATCH
    # ========================================================

    if status == "MATCHED_WITH_AMOUNT_MISMATCH":

        return {
            "exception_type":
                "AMOUNT_MISMATCH",

            "severity":
                calculate_severity(
                    "AMOUNT_MISMATCH",
                    amount_difference,
                    confidence,
                ),

            "confidence":
                round(confidence, 4),

            "amount_at_risk":
                round(
                    amount_difference,
                    2,
                ),

            "explanation":
                (
                    f"The transaction identity appears "
                    f"strong, but the bank settlement "
                    f"amount differs by "
                    f"₹{amount_difference:.2f}. "
                    f"This could indicate a refund, "
                    f"partial settlement, adjustment "
                    f"or incorrect settlement."
                ),

            "recommended_action":
                (
                    "Investigate the settlement ledger "
                    "and associated adjustments."
                ),
        }

    # ========================================================
    # AMBIGUOUS
    # ========================================================

    if status == "AMBIGUOUS":

        return {
            "exception_type":
                "AMBIGUOUS_MATCH",

            "severity":
                calculate_severity(
                    "AMBIGUOUS_MATCH",
                    transaction_amount,
                    confidence,
                ),

            "confidence":
                round(confidence, 4),

            "amount_at_risk":
                round(
                    transaction_amount,
                    2,
                ),

            "explanation":
                (
                    "Multiple bank records have "
                    "similar matching scores, so the "
                    "system cannot safely determine "
                    "which settlement belongs to "
                    "the transaction."
                ),

            "recommended_action":
                (
                    "Send to AI investigation or "
                    "manual finance-ops review."
                ),
        }

    # ========================================================
    # REVIEW
    # ========================================================

    if status == "REVIEW":

        return {
            "exception_type":
                "LOW_CONFIDENCE",

            "severity":
                calculate_severity(
                    "LOW_CONFIDENCE",
                    transaction_amount,
                    confidence,
                ),

            "confidence":
                round(confidence, 4),

            "amount_at_risk":
                round(
                    transaction_amount,
                    2,
                ),

            "explanation":
                (
                    "A potential bank settlement was "
                    "identified, but its matching "
                    "confidence is below the automatic "
                    "reconciliation threshold."
                ),

            "recommended_action":
                (
                    "Review transaction reference, "
                    "merchant, amount and settlement date."
                ),
        }

    # ========================================================
    # UNKNOWN STATUS
    # ========================================================

    return {
        "exception_type":
            "UNCLASSIFIED_EXCEPTION",

        "severity":
            "MEDIUM",

        "confidence":
            round(confidence, 4),

        "amount_at_risk":
            round(
                transaction_amount,
                2,
            ),

        "explanation":
            (
                f"The reconciliation engine returned "
                f"an unexpected status: {status}."
            ),

        "recommended_action":
            (
                "Investigate the reconciliation "
                "decision and classify manually."
            ),
    }


# ============================================================
# CLASSIFY COMPLETE DATASET
# ============================================================

def classify_reconciliation_results(
    reconciliation_results,
    gateway=None,
):
    """
    Classify all reconciliation results.

    Returns one row for every exception.
    """

    results = []

    # --------------------------------------------------------
    # Optional gateway lookup
    # --------------------------------------------------------

    gateway_lookup = {}

    if gateway is not None:

        for _, gateway_row in gateway.iterrows():

            transaction_id = str(
                gateway_row[
                    "gateway_transaction_id"
                ]
            ).strip().upper()

            gateway_lookup[
                transaction_id
            ] = gateway_row

    # --------------------------------------------------------
    # Process results
    # --------------------------------------------------------

    for _, row in (
        reconciliation_results.iterrows()
    ):

        exception = classify_exception(
            row
        )

        if exception is None:
            continue

        transaction_id = str(
            row.get(
                "gateway_transaction_id",
                "",
            )
        ).strip().upper()

        gateway_row = (
            gateway_lookup.get(
                transaction_id
            )
        )

        # ----------------------------------------------------
        # Amount fallback
        # ----------------------------------------------------

        transaction_amount = row.get(
            "amount",
            None,
        )

        if (
            transaction_amount is None
            or pd.isna(transaction_amount)
        ):

            if gateway_row is not None:

                transaction_amount = (
                    gateway_row["amount"]
                )

            else:

                transaction_amount = (
                    row.get(
                        "original_amount",
                        0.0,
                    )
                )

        # ----------------------------------------------------
        # Merchant
        # ----------------------------------------------------

        merchant_name = row.get(
            "merchant_name",
            None,
        )

        if (
            merchant_name is None
            or pd.isna(merchant_name)
        ):

            if gateway_row is not None:

                merchant_name = (
                    gateway_row[
                        "merchant_name"
                    ]
                )

        # ----------------------------------------------------
        # Currency
        # ----------------------------------------------------

        currency = row.get(
            "currency",
            None,
        )

        if (
            currency is None
            or pd.isna(currency)
        ):

            if gateway_row is not None:

                currency = gateway_row[
                    "currency"
                ]

        # ----------------------------------------------------
        # Build final exception
        # ----------------------------------------------------

        exception_record = {
            "transaction_id":
                transaction_id,

            "bank_reference":
                row.get(
                    "bank_reference",
                    None,
                ),

            "transaction_amount":
                transaction_amount,

            "currency":
                currency,

            "merchant_name":
                merchant_name,

            "reconciliation_status":
                row.get(
                    "reconciliation_status",
                    None,
                ),

            "reconciliation_method":
                row.get(
                    "reconciliation_method",
                    None,
                ),

            "exception_type":
                exception[
                    "exception_type"
                ],

            "severity":
                exception[
                    "severity"
                ],

            "confidence":
                exception[
                    "confidence"
                ],

            "amount_at_risk":
                exception[
                    "amount_at_risk"
                ],

            "amount_difference":
                row.get(
                    "amount_difference",
                    0.0,
                ),

            "explanation":
                exception[
                    "explanation"
                ],

            "recommended_action":
                exception[
                    "recommended_action"
                ],
        }

        results.append(
            exception_record
        )

    if not results:

        return pd.DataFrame(
            columns=[
                "transaction_id",
                "bank_reference",
                "transaction_amount",
                "currency",
                "merchant_name",
                "reconciliation_status",
                "reconciliation_method",
                "exception_type",
                "severity",
                "confidence",
                "amount_at_risk",
                "amount_difference",
                "explanation",
                "recommended_action",
            ]
        )

    return pd.DataFrame(
        results
    )


# ============================================================
# SUMMARY
# ============================================================

def print_exception_summary(
    exceptions,
):
    """
    Print exception statistics.
    """

    print("\n")
    print("=" * 60)
    print(
        "RECONCILEAI — EXCEPTION ANALYSIS"
    )
    print("=" * 60)

    print(
        f"\nTotal exceptions: "
        f"{len(exceptions)}"
    )

    if exceptions.empty:

        print(
            "\nNo exceptions detected."
        )

        return

    print(
        "\nEXCEPTION TYPES"
    )

    print("-" * 60)

    print(
        exceptions[
            "exception_type"
        ]
        .value_counts()
        .to_string()
    )

    print(
        "\nSEVERITY"
    )

    print("-" * 60)

    print(
        exceptions[
            "severity"
        ]
        .value_counts()
        .to_string()
    )

    total_at_risk = (
        exceptions[
            "amount_at_risk"
        ]
        .fillna(0)
        .sum()
    )

    print(
        f"\nTotal amount at risk: "
        f"₹{total_at_risk:,.2f}"
    )

    print(
        "\nTOP EXCEPTIONS BY FINANCIAL IMPACT"
    )

    print("-" * 60)

    columns = [
        "transaction_id",
        "exception_type",
        "severity",
        "amount_at_risk",
        "confidence",
    ]

    print(
        exceptions[
            columns
        ]
        .sort_values(
            "amount_at_risk",
            ascending=False,
        )
        .head(10)
        .to_string(index=False)
    )


# ============================================================
# SAVE
# ============================================================

def save_exceptions(
    exceptions,
):
    """
    Save exception report.
    """

    PROCESSED_DATA_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    output_file = (
        PROCESSED_DATA_DIR
        / "exceptions.csv"
    )

    exceptions.to_csv(
        output_file,
        index=False,
    )

    print(
        f"\nException report saved to:"
        f"\n{output_file}"
    )


# ============================================================
# MAIN
# ============================================================

def main():

    print("=" * 60)
    print(
        "ReconcileAI — Exception Classifier"
    )
    print("=" * 60)

    input_file = (
        PROCESSED_DATA_DIR
        / "reconciliation_results.csv"
    )

    gateway_file = (
        BASE_DIR
        / "data"
        / "raw"
        / "gateway_transactions.csv"
    )

    # --------------------------------------------------------
    # Load reconciliation results
    # --------------------------------------------------------

    if not input_file.exists():

        raise FileNotFoundError(
            f"Reconciliation results not found:\n"
            f"{input_file}\n\n"
            "Run the reconciliation pipeline first."
        )

    reconciliation_results = pd.read_csv(
        input_file
    )

    # --------------------------------------------------------
    # Load gateway data
    # --------------------------------------------------------

    gateway = None

    if gateway_file.exists():

        gateway = pd.read_csv(
            gateway_file
        )

    print(
        f"\nReconciliation records: "
        f"{len(reconciliation_results)}"
    )

    # --------------------------------------------------------
    # Classify
    # --------------------------------------------------------

    exceptions = (
        classify_reconciliation_results(
            reconciliation_results,
            gateway,
        )
    )

    # --------------------------------------------------------
    # Summary
    # --------------------------------------------------------

    print_exception_summary(
        exceptions
    )

    # --------------------------------------------------------
    # Save
    # --------------------------------------------------------

    save_exceptions(
        exceptions
    )

    print(
        "\nException classification complete."
    )


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":
    main()