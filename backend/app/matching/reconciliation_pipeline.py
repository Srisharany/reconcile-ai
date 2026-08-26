from pathlib import Path

import pandas as pd

from app.matching.fuzzy_matcher import (
    fuzzy_match_transaction,
)


# ============================================================
# PATHS
# ============================================================

BASE_DIR = Path(__file__).resolve().parents[2]

RAW_DATA_DIR = BASE_DIR / "data" / "raw"
PROCESSED_DATA_DIR = BASE_DIR / "data" / "processed"


# ============================================================
# PASS 1 — EXACT GATEWAY → BANK MATCHING
# ============================================================

def run_exact_gateway_bank_matching(gateway, bank):
    """
    Pass 1:
    Deterministic Gateway → Bank reconciliation.

    Exact match requires:
        - transaction reference
        - amount
        - currency
    """

    bank_lookup = {}

    for _, row in bank.iterrows():

        reference = (
            str(row["transaction_reference"])
            .strip()
            .upper()
        )

        bank_lookup.setdefault(
            reference,
            []
        ).append(row)

    results = []

    for _, gateway_row in gateway.iterrows():

        gateway_id = (
            str(
                gateway_row[
                    "gateway_transaction_id"
                ]
            )
            .strip()
            .upper()
        )

        gateway_amount = float(
            gateway_row["amount"]
        )

        gateway_currency = (
            gateway_row["currency"]
        )

        candidates = bank_lookup.get(
            gateway_id,
            []
        )

        exact_matches = []

        for bank_row in candidates:

            try:
                bank_amount = float(
                    bank_row["credit_amount"]
                )
            except (
                TypeError,
                ValueError,
            ):
                continue

            if (
                bank_amount == gateway_amount
                and
                bank_row["currency"]
                == gateway_currency
            ):
                exact_matches.append(
                    bank_row
                )

        # ----------------------------------------------------
        # Exactly one match
        # ----------------------------------------------------

        if len(exact_matches) == 1:

            bank_row = exact_matches[0]

            results.append(
                {
                    "gateway_transaction_id":
                        gateway_id,

                    "bank_reference":
                        bank_row[
                            "bank_reference"
                        ],

                    "status":
                        "MATCHED",

                    "method":
                        "EXACT",

                    "confidence":
                        1.0,

                    "reason":
                        (
                            "Exact transaction "
                            "reference, amount "
                            "and currency match."
                        ),

                    "recommended_action":
                        "Auto-reconcile.",
                }
            )

        # ----------------------------------------------------
        # Duplicate
        # ----------------------------------------------------

        elif len(exact_matches) > 1:

            results.append(
                {
                    "gateway_transaction_id":
                        gateway_id,

                    "bank_reference":
                        exact_matches[0][
                            "bank_reference"
                        ],

                    "status":
                        "DUPLICATE",

                    "method":
                        "EXACT",

                    "confidence":
                        1.0,

                    "reason":
                        (
                            "Multiple bank records "
                            "share the same transaction "
                            "reference and amount."
                        ),

                    "recommended_action":
                        (
                            "Investigate duplicate "
                            "settlement records."
                        ),
                }
            )

        # ----------------------------------------------------
        # No exact match
        # ----------------------------------------------------

        else:

            results.append(
                {
                    "gateway_transaction_id":
                        gateway_id,

                    "bank_reference":
                        None,

                    "status":
                        "UNMATCHED",

                    "method":
                        "EXACT",

                    "confidence":
                        0.0,

                    "reason":
                        (
                            "No exact bank settlement "
                            "was found."
                        ),

                    "recommended_action":
                        (
                            "Send to Pass 2 fuzzy "
                            "matching."
                        ),
                }
            )

    return pd.DataFrame(results)


# ============================================================
# PASS 2 — FUZZY MATCHING
# ============================================================

def run_fuzzy_on_unmatched(
    gateway,
    bank,
    exact_results,
):
    """
    Pass 2 runs ONLY on transactions that Pass 1
    could not reconcile.
    """

    unmatched_ids = set(
        exact_results.loc[
            exact_results["status"]
            == "UNMATCHED",
            "gateway_transaction_id",
        ]
    )

    gateway_ids = (
        gateway[
            "gateway_transaction_id"
        ]
        .astype(str)
        .str.upper()
    )

    unmatched_gateway = gateway[
        gateway_ids.isin(
            unmatched_ids
        )
    ].copy()

    print(
        f"\nTransactions entering Pass 2: "
        f"{len(unmatched_gateway)}"
    )

    results = []

    for _, gateway_row in (
        unmatched_gateway.iterrows()
    ):

        result = fuzzy_match_transaction(
            gateway_row,
            bank,
        )

        results.append(result)

    if not results:

        return pd.DataFrame()

    return pd.DataFrame(results)


# ============================================================
# COMBINE RESULTS
# ============================================================

def combine_results(
    exact_results,
    fuzzy_results,
):
    """
    Combine Pass 1 and Pass 2 into one final table.
    """

    frames = []

    # --------------------------------------------------------
    # Pass 1 resolved records
    # --------------------------------------------------------

    exact_resolved = exact_results[
        exact_results["status"]
        != "UNMATCHED"
    ].copy()

    if not exact_resolved.empty:

        exact_resolved = (
            exact_resolved.rename(
                columns={
                    "status":
                        "reconciliation_status",

                    "method":
                        "reconciliation_method",

                    "confidence":
                        "reconciliation_confidence",

                    "reason":
                        "reconciliation_reason",
                }
            )
        )

        frames.append(
            exact_resolved
        )

    # --------------------------------------------------------
    # Pass 2 records
    # --------------------------------------------------------

    if (
        fuzzy_results is not None
        and not fuzzy_results.empty
    ):

        fuzzy_final = (
            fuzzy_results.rename(
                columns={
                    "fuzzy_status":
                        "reconciliation_status",

                    "fuzzy_method":
                        "reconciliation_method",

                    "fuzzy_confidence":
                        "reconciliation_confidence",

                    "reason":
                        "reconciliation_reason",
                }
            )
        )

        frames.append(
            fuzzy_final
        )

    # --------------------------------------------------------
    # Nothing
    # --------------------------------------------------------

    if not frames:

        return pd.DataFrame()

    final = pd.concat(
        frames,
        ignore_index=True,
        sort=False,
    )

    return final


# ============================================================
# SUMMARY
# ============================================================

def print_summary(
    exact_results,
    fuzzy_results,
    final_results,
):
    """
    Print pipeline summary.
    """

    print("\n")
    print("=" * 60)
    print(
        "RECONCILEAI — RECONCILIATION PIPELINE"
    )
    print("=" * 60)

    # --------------------------------------------------------
    # Pass 1
    # --------------------------------------------------------

    print(
        "\nPASS 1 — EXACT MATCHING"
    )

    print("-" * 60)

    print(
        exact_results[
            "status"
        ]
        .value_counts()
        .to_string()
    )

    unmatched_count = int(
        (
            exact_results["status"]
            == "UNMATCHED"
        ).sum()
    )

    print(
        f"\nPassed to Pass 2: "
        f"{unmatched_count}"
    )

    # --------------------------------------------------------
    # Pass 2
    # --------------------------------------------------------

    print(
        "\nPASS 2 — FUZZY MATCHING"
    )

    print("-" * 60)

    if (
        fuzzy_results is None
        or fuzzy_results.empty
    ):

        print(
            "No transactions required "
            "fuzzy matching."
        )

    else:

        print(
            fuzzy_results[
                "fuzzy_status"
            ]
            .value_counts()
            .to_string()
        )

    # --------------------------------------------------------
    # Final
    # --------------------------------------------------------

    print(
        "\nFINAL PIPELINE"
    )

    print("-" * 60)

    if final_results.empty:

        print(
            "No reconciliation results."
        )

    else:

        print(
            final_results[
                "reconciliation_status"
            ]
            .value_counts()
            .to_string()
        )


# ============================================================
# SAVE RESULTS
# ============================================================

def save_results(
    exact_results,
    fuzzy_results,
    final_results,
):
    """
    Save all pipeline outputs.
    """

    PROCESSED_DATA_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    exact_file = (
        PROCESSED_DATA_DIR
        / "pass1_exact_results.csv"
    )

    fuzzy_file = (
        PROCESSED_DATA_DIR
        / "pass2_fuzzy_results.csv"
    )

    final_file = (
        PROCESSED_DATA_DIR
        / "reconciliation_results.csv"
    )

    exact_results.to_csv(
        exact_file,
        index=False,
    )

    if (
        fuzzy_results is not None
        and not fuzzy_results.empty
    ):

        fuzzy_results.to_csv(
            fuzzy_file,
            index=False,
        )

    else:

        pd.DataFrame().to_csv(
            fuzzy_file,
            index=False,
        )

    final_results.to_csv(
        final_file,
        index=False,
    )

    print(
        "\nFILES CREATED"
    )

    print(
        f"Pass 1:"
        f"\n{exact_file}"
    )

    print(
        f"\nPass 2:"
        f"\n{fuzzy_file}"
    )

    print(
        f"\nFinal:"
        f"\n{final_file}"
    )


# ============================================================
# MAIN PIPELINE
# ============================================================

def main():

    print("=" * 60)

    print(
        "ReconcileAI — Multi-Stage "
        "Reconciliation Pipeline"
    )

    print("=" * 60)

    # --------------------------------------------------------
    # Load data
    # --------------------------------------------------------

    print(
        "\nLoading datasets..."
    )

    gateway = pd.read_csv(
        RAW_DATA_DIR
        / "gateway_transactions.csv"
    )

    bank = pd.read_csv(
        RAW_DATA_DIR
        / "bank_statements.csv"
    )

    print(
        f"Gateway transactions: "
        f"{len(gateway)}"
    )

    print(
        f"Bank statements: "
        f"{len(bank)}"
    )

    # --------------------------------------------------------
    # PASS 1
    # --------------------------------------------------------

    print(
        "\nRunning Pass 1 — "
        "Exact Matching..."
    )

    exact_results = (
        run_exact_gateway_bank_matching(
            gateway,
            bank,
        )
    )

    # --------------------------------------------------------
    # PASS 2
    # --------------------------------------------------------

    print(
        "\nRunning Pass 2 — "
        "Fuzzy Matching on unresolved "
        "transactions..."
    )

    fuzzy_results = (
        run_fuzzy_on_unmatched(
            gateway,
            bank,
            exact_results,
        )
    )

    # --------------------------------------------------------
    # Combine
    # --------------------------------------------------------

    final_results = combine_results(
        exact_results,
        fuzzy_results,
    )

    # --------------------------------------------------------
    # Summary
    # --------------------------------------------------------

    print_summary(
        exact_results,
        fuzzy_results,
        final_results,
    )

    # --------------------------------------------------------
    # Save
    # --------------------------------------------------------

    save_results(
        exact_results,
        fuzzy_results,
        final_results,
    )

    print(
        "\nReconciliation pipeline complete."
    )


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":
    main()