import json
from pathlib import Path

import pandas as pd


# ============================================================
# PATHS
# ============================================================

BASE_DIR = Path(__file__).resolve().parents[2]

PROCESSED_DATA_DIR = BASE_DIR / "data" / "processed"


RECONCILIATION_FILE = (
    PROCESSED_DATA_DIR / "reconciliation_results.csv"
)

EXCEPTIONS_FILE = (
    PROCESSED_DATA_DIR / "exceptions.csv"
)

AI_FILE = (
    PROCESSED_DATA_DIR / "ai_investigations.json"
)

OUTPUT_CSV = (
    PROCESSED_DATA_DIR / "final_reconciliation_report.csv"
)

OUTPUT_JSON = (
    PROCESSED_DATA_DIR / "final_reconciliation_report.json"
)


# ============================================================
# HELPERS
# ============================================================

def safe_float(value, default=0.0):
    """
    Safely convert a value to float.
    """

    try:

        if pd.isna(value):
            return default

        return float(value)

    except (
        TypeError,
        ValueError,
    ):

        return default


def load_ai_investigations():
    """
    Load Pass 3 AI investigation results.
    """

    if not AI_FILE.exists():

        print(
            "WARNING: AI investigation file not found."
        )

        return {}

    with open(
        AI_FILE,
        "r",
        encoding="utf-8",
    ) as file:

        data = json.load(file)

    investigations = {}

    # Support either a list or dictionary format.
    if isinstance(data, list):

        for item in data:

            transaction_id = (
                item.get("transaction_id")
            )

            if transaction_id:

                investigations[
                    transaction_id
                ] = item

    elif isinstance(data, dict):

        # If wrapped inside a results field.
        if isinstance(
            data.get("investigations"),
            list,
        ):

            for item in data["investigations"]:

                transaction_id = (
                    item.get("transaction_id")
                )

                if transaction_id:

                    investigations[
                        transaction_id
                    ] = item

        else:

            for transaction_id, item in data.items():

                if isinstance(item, dict):

                    investigations[
                        transaction_id
                    ] = item

    return investigations


# ============================================================
# DECISION ENGINE
# ============================================================

def determine_final_decision(
    reconciliation_status,
    exception_type=None,
    severity=None,
    ai_result=None,
):
    """
    Determine the operational decision.

    IMPORTANT:
    AI never independently authorizes resolution.
    """

    reconciliation_status = str(
        reconciliation_status
        or ""
    ).upper()

    exception_type = str(
        exception_type
        or ""
    ).upper()

    severity = str(
        severity
        or ""
    ).upper()

    # --------------------------------------------------------
    # Normal reconciled transactions
    # --------------------------------------------------------

    if reconciliation_status == "MATCHED":

        return (
            "RECONCILED",
            "No exception detected.",
        )

    # --------------------------------------------------------
    # Duplicate
    # --------------------------------------------------------

    if (
        reconciliation_status == "DUPLICATE"
        or exception_type
        == "DUPLICATE_TRANSACTION"
    ):

        return (
            "MANUAL_REVIEW",
            "Investigate duplicate settlement records.",
        )

    # --------------------------------------------------------
    # Amount mismatch
    # --------------------------------------------------------

    if (
        reconciliation_status
        == "MATCHED_WITH_AMOUNT_MISMATCH"
        or exception_type
        == "AMOUNT_MISMATCH"
    ):

        return (
            "MANUAL_REVIEW",
            "Investigate settlement amount discrepancy.",
        )

    # --------------------------------------------------------
    # Possible fee
    # --------------------------------------------------------

    if (
        reconciliation_status
        == "MATCHED_WITH_FEE"
        or exception_type
        == "POSSIBLE_FEE"
    ):

        return (
            "MANUAL_REVIEW",
            "Verify applicable fee or settlement adjustment.",
        )

    # --------------------------------------------------------
    # Ambiguous
    # --------------------------------------------------------

    if (
        reconciliation_status
        == "AMBIGUOUS"
        or exception_type
        == "AMBIGUOUS_MATCH"
    ):

        return (
            "MANUAL_REVIEW",
            "Review competing reconciliation candidates.",
        )

    # --------------------------------------------------------
    # Low confidence
    # --------------------------------------------------------

    if (
        reconciliation_status
        == "REVIEW"
        or exception_type
        == "LOW_CONFIDENCE"
    ):

        return (
            "MANUAL_REVIEW",
            "Review low-confidence reconciliation.",
        )

    # --------------------------------------------------------
    # Missing settlement
    # --------------------------------------------------------

    if (
        reconciliation_status
        == "UNRESOLVED"
        or exception_type
        == "MISSING_SETTLEMENT"
    ):

        return (
            "INVESTIGATE",
            "Search settlement records and verify gateway status.",
        )

    # --------------------------------------------------------
    # Fallback
    # --------------------------------------------------------

    return (
        "MANUAL_REVIEW",
        "Review reconciliation exception.",
    )


# ============================================================
# BUILD REPORT
# ============================================================

def build_final_report():

    print("=" * 60)

    print(
        "ReconcileAI — Pass 4: Final Decision Engine"
    )

    print("=" * 60)

    # --------------------------------------------------------
    # Load reconciliation results
    # --------------------------------------------------------

    if not RECONCILIATION_FILE.exists():

        raise FileNotFoundError(
            f"Missing reconciliation file:\n"
            f"{RECONCILIATION_FILE}"
        )

    reconciliation = pd.read_csv(
        RECONCILIATION_FILE
    )

    print(
        f"\nReconciliation records: "
        f"{len(reconciliation)}"
    )

    # --------------------------------------------------------
    # Load exceptions
    # --------------------------------------------------------

    if EXCEPTIONS_FILE.exists():

        exceptions = pd.read_csv(
            EXCEPTIONS_FILE
        )

        print(
            f"Exceptions: "
            f"{len(exceptions)}"
        )

    else:

        exceptions = pd.DataFrame()

        print(
            "Exceptions file not found."
        )

    # --------------------------------------------------------
    # Load AI investigations
    # --------------------------------------------------------

    ai_investigations = (
        load_ai_investigations()
    )

    print(
        f"AI investigations: "
        f"{len(ai_investigations)}"
    )

    # --------------------------------------------------------
    # Build exception lookup
    # --------------------------------------------------------

    exception_lookup = {}

    if not exceptions.empty:

        for _, row in exceptions.iterrows():

            transaction_id = str(
                row.get(
                    "transaction_id",
                    ""
                )
            ).strip()

            if transaction_id:

                exception_lookup[
                    transaction_id
                ] = row.to_dict()

    # --------------------------------------------------------
    # Build final records
    # --------------------------------------------------------

    final_records = []

    print(
        "\nBuilding final decisions..."
    )

    for _, row in reconciliation.iterrows():

        # ----------------------------------------------------
        # Transaction ID
        # ----------------------------------------------------

        transaction_id = str(
            row.get(
                "gateway_transaction_id",
                row.get(
                    "transaction_id",
                    ""
                ),
            )
        ).strip()

        status = str(
            row.get(
                "reconciliation_status",
                ""
            )
        ).strip()

        confidence = safe_float(
            row.get(
                "reconciliation_confidence",
                0.0
            )
        )

        # ----------------------------------------------------
        # Exception
        # ----------------------------------------------------

        exception = (
            exception_lookup.get(
                transaction_id,
                {}
            )
        )

        exception_type = exception.get(
            "exception_type"
        )

        severity = exception.get(
            "severity"
        )

        amount_at_risk = safe_float(
            exception.get(
                "amount_at_risk",
                0.0
            )
        )

        # ----------------------------------------------------
        # AI
        # ----------------------------------------------------

        ai_result = (
            ai_investigations.get(
                transaction_id
            )
        )

        ai_status = None
        ai_confidence = None
        ai_likely_cause = None
        ai_reasoning = None
        ai_action = None
        human_review = False

        if ai_result:

            ai_status = ai_result.get(
                "ai_status",
                "SUCCESS"
            )

            ai_confidence = safe_float(
                ai_result.get(
                    "confidence",
                    0.0
                )
            )

            ai_likely_cause = (
                ai_result.get(
                    "likely_cause"
                )
            )

            ai_reasoning = (
                ai_result.get(
                    "reasoning_summary"
                )
            )

            ai_action = (
                ai_result.get(
                    "recommended_action"
                )
            )

            human_review = bool(
                ai_result.get(
                    "requires_human_review",
                    True
                )
            )

        # ----------------------------------------------------
        # Final decision
        # ----------------------------------------------------

        final_decision, action = (
            determine_final_decision(
                status,
                exception_type,
                severity,
                ai_result,
            )
        )

        # ----------------------------------------------------
        # Safety rule
        # ----------------------------------------------------

        if ai_result:

            # AI can NEVER auto-resolve
            human_review = True

        # ----------------------------------------------------
        # Prefer AI recommendation when available
        # ----------------------------------------------------

        recommended_action = (
            ai_action
            if ai_action
            else action
        )

        # ----------------------------------------------------
        # Final record
        # ----------------------------------------------------

        final_records.append(
            {
                "transaction_id":
                    transaction_id,

                "bank_reference":
                    row.get(
                        "bank_reference"
                    ),

                "reconciliation_status":
                    status,

                "reconciliation_method":
                    row.get(
                        "reconciliation_method"
                    ),

                "reconciliation_confidence":
                    confidence,

                "exception_type":
                    exception_type,

                "severity":
                    severity,

                "amount_at_risk":
                    amount_at_risk,

                "ai_status":
                    ai_status,

                "ai_confidence":
                    ai_confidence,

                "ai_likely_cause":
                    ai_likely_cause,

                "ai_reasoning":
                    ai_reasoning,

                "final_decision":
                    final_decision,

                "recommended_action":
                    recommended_action,

                "requires_human_review":
                    human_review,
            }
        )

    return pd.DataFrame(
        final_records
    )


# ============================================================
# KPI SUMMARY
# ============================================================

def calculate_kpis(
    report
):

    total = len(report)

    reconciled = int(
        (
            report[
                "final_decision"
            ]
            == "RECONCILED"
        ).sum()
    )

    manual_review = int(
        (
            report[
                "final_decision"
            ]
            == "MANUAL_REVIEW"
        ).sum()
    )

    investigate = int(
        (
            report[
                "final_decision"
            ]
            == "INVESTIGATE"
        ).sum()
    )

    exceptions = total - reconciled

    exception_rate = (
        exceptions / total
        if total
        else 0
    )

    total_amount_at_risk = (
        report[
            "amount_at_risk"
        ]
        .fillna(0)
        .sum()
    )

    critical = int(
        (
            report[
                "severity"
            ]
            == "CRITICAL"
        ).sum()
    )

    high = int(
        (
            report[
                "severity"
            ]
            == "HIGH"
        ).sum()
    )

    medium = int(
        (
            report[
                "severity"
            ]
            == "MEDIUM"
        ).sum()
    )

    low = int(
        (
            report[
                "severity"
            ]
            == "LOW"
        ).sum()
    )

    ai_cases = int(
        report[
            "ai_status"
        ]
        .notna()
        .sum()
    )

    return {
        "total_transactions":
            total,

        "reconciled_transactions":
            reconciled,

        "exception_transactions":
            exceptions,

        "exception_rate":
            round(
                exception_rate,
                4
            ),

        "manual_review_cases":
            manual_review,

        "investigation_cases":
            investigate,

        "critical_exceptions":
            critical,

        "high_exceptions":
            high,

        "medium_exceptions":
            medium,

        "low_exceptions":
            low,

        "total_amount_at_risk":
            round(
                total_amount_at_risk,
                2
            ),

        "ai_investigated_cases":
            ai_cases,

        "ai_auto_resolution":
            0,
    }


# ============================================================
# SAVE
# ============================================================

def save_report(
    report,
    kpis,
):

    PROCESSED_DATA_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    # --------------------------------------------------------
    # CSV
    # --------------------------------------------------------

    report.to_csv(
        OUTPUT_CSV,
        index=False,
    )

    # --------------------------------------------------------
    # JSON
    # --------------------------------------------------------

    output = {
        "project":
            "ReconcileAI",

        "report_type":
            "Final Reconciliation Report",

        "kpis":
            kpis,

        "records":
            report.to_dict(
                orient="records"
            ),
    }

    with open(
        OUTPUT_JSON,
        "w",
        encoding="utf-8",
    ) as file:

        json.dump(
            output,
            file,
            indent=2,
            ensure_ascii=False,
            default=str,
        )

    print(
        "\nFILES CREATED"
    )

    print(
        f"CSV:\n{OUTPUT_CSV}"
    )

    print(
        f"\nJSON:\n{OUTPUT_JSON}"
    )


# ============================================================
# PRINT SUMMARY
# ============================================================

def print_summary(
    report,
    kpis,
):

    print("\n")
    print("=" * 60)
    print(
        "FINAL RECONCILIATION SUMMARY"
    )
    print("=" * 60)

    print(
        f"\nTotal transactions: "
        f"{kpis['total_transactions']}"
    )

    print(
        f"Reconciled: "
        f"{kpis['reconciled_transactions']}"
    )

    print(
        f"Exceptions: "
        f"{kpis['exception_transactions']}"
    )

    print(
        f"Exception rate: "
        f"{kpis['exception_rate'] * 100:.2f}%"
    )

    print(
        f"Manual review: "
        f"{kpis['manual_review_cases']}"
    )

    print(
        f"Investigation required: "
        f"{kpis['investigation_cases']}"
    )

    print(
        f"Amount at risk: "
        f"₹{kpis['total_amount_at_risk']:,.2f}"
    )

    print(
        "\nSEVERITY"
    )

    print("-" * 60)

    print(
        f"Critical: "
        f"{kpis['critical_exceptions']}"
    )

    print(
        f"High: "
        f"{kpis['high_exceptions']}"
    )

    print(
        f"Medium: "
        f"{kpis['medium_exceptions']}"
    )

    print(
        f"Low: "
        f"{kpis['low_exceptions']}"
    )

    print(
        "\nDECISIONS"
    )

    print("-" * 60)

    print(
        report[
            "final_decision"
        ]
        .value_counts()
        .to_string()
    )

    print(
        "\nAI INVESTIGATION"
    )

    print("-" * 60)

    print(
        f"AI investigated: "
        f"{kpis['ai_investigated_cases']}"
    )

    print(
        "AI auto-resolution: 0"
    )


# ============================================================
# MAIN
# ============================================================

def main():

    report = build_final_report()

    kpis = calculate_kpis(
        report
    )

    print_summary(
        report,
        kpis,
    )

    save_report(
        report,
        kpis,
    )

    print(
        "\nPass 4 complete."
    )


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":
    main()