import json
import math
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

    Handles:
    - None
    - NaN
    - Infinity
    - empty strings
    - invalid values
    """

    try:

        if value is None:
            return default

        if pd.isna(value):
            return default

        number = float(value)

        if not math.isfinite(number):
            return default

        return number

    except (
        TypeError,
        ValueError,
    ):

        return default


def safe_string(value, default=None):
    """
    Safely convert a value to string.
    """

    if value is None:
        return default

    try:

        if pd.isna(value):
            return default

    except (
        TypeError,
        ValueError,
    ):

        pass

    value = str(value).strip()

    if not value:
        return default

    return value


def clean_dataframe_for_json(dataframe):
    """
    Replace NaN and infinite values with None
    before writing JSON.
    """

    dataframe = dataframe.copy()

    dataframe = dataframe.replace(
        [float("inf"), float("-inf")],
        None,
    )

    dataframe = dataframe.where(
        pd.notna(dataframe),
        None,
    )

    return dataframe


# ============================================================
# LOAD AI INVESTIGATIONS
# ============================================================

def load_ai_investigations():
    """
    Load Pass 3 AI investigation results.

    Supports:
    1. List format
    2. {"investigations": [...]}
    3. Dictionary keyed by transaction ID
    """

    if not AI_FILE.exists():

        print(
            "WARNING: AI investigation file not found."
        )

        return {}

    try:

        with open(
            AI_FILE,
            "r",
            encoding="utf-8",
        ) as file:

            data = json.load(file)

    except (
        json.JSONDecodeError,
        OSError,
    ) as error:

        print(
            f"WARNING: Could not load AI investigations: "
            f"{error}"
        )

        return {}

    investigations = {}

    # --------------------------------------------------------
    # LIST
    # --------------------------------------------------------

    if isinstance(data, list):

        for item in data:

            if not isinstance(item, dict):
                continue

            transaction_id = safe_string(
                item.get(
                    "transaction_id"
                )
            )

            if transaction_id:

                investigations[
                    transaction_id
                ] = item

    # --------------------------------------------------------
    # DICTIONARY
    # --------------------------------------------------------

    elif isinstance(data, dict):

        # Wrapped format
        if isinstance(
            data.get("investigations"),
            list,
        ):

            for item in data["investigations"]:

                if not isinstance(item, dict):
                    continue

                transaction_id = safe_string(
                    item.get(
                        "transaction_id"
                    )
                )

                if transaction_id:

                    investigations[
                        transaction_id
                    ] = item

        # Direct dictionary format
        else:

            for transaction_id, item in data.items():

                if not isinstance(item, dict):
                    continue

                transaction_id = safe_string(
                    transaction_id
                )

                if transaction_id:

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
    Determine the final operational decision.

    IMPORTANT SAFETY RULE:

    AI NEVER independently authorizes a financial action.

    Pass 4 deterministic business rules always control
    the final decision.
    """

    reconciliation_status = (
        safe_string(
            reconciliation_status,
            "",
        )
        or ""
    ).upper()

    exception_type = (
        safe_string(
            exception_type,
            "",
        )
        or ""
    ).upper()

    severity = (
        safe_string(
            severity,
            "",
        )
        or ""
    ).upper()

    # --------------------------------------------------------
    # NORMAL RECONCILED TRANSACTION
    # --------------------------------------------------------

    if reconciliation_status == "MATCHED":

        return (
            "RECONCILED",
            "No exception detected.",
        )

    # --------------------------------------------------------
    # DUPLICATE
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
    # AMOUNT MISMATCH
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
    # POSSIBLE FEE
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
    # AMBIGUOUS
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
    # LOW CONFIDENCE
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
    # MISSING SETTLEMENT
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
    # FALLBACK
    # --------------------------------------------------------

    return (
        "MANUAL_REVIEW",
        "Review reconciliation exception.",
    )


# ============================================================
# BUILD FINAL REPORT
# ============================================================

def build_final_report():

    print("=" * 60)

    print(
        "ReconcileAI — Pass 4: Final Decision Engine"
    )

    print("=" * 60)

    print(
        f"\nProcessed data directory:\n"
        f"{PROCESSED_DATA_DIR}"
    )

    # --------------------------------------------------------
    # LOAD RECONCILIATION RESULTS
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

    print(
        "Reconciliation columns:",
        reconciliation.columns.tolist(),
    )

    # --------------------------------------------------------
    # LOAD EXCEPTIONS
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
    # LOAD AI INVESTIGATIONS
    # --------------------------------------------------------

    ai_investigations = (
        load_ai_investigations()
    )

    print(
        f"AI investigations: "
        f"{len(ai_investigations)}"
    )

    # --------------------------------------------------------
    # BUILD EXCEPTION LOOKUP
    # --------------------------------------------------------

    exception_lookup = {}

    if not exceptions.empty:

        for _, row in exceptions.iterrows():

            transaction_id = safe_string(
                row.get(
                    "transaction_id",
                    "",
                )
            )

            if transaction_id:

                exception_lookup[
                    transaction_id
                ] = row.to_dict()

    # --------------------------------------------------------
    # BUILD FINAL RECORDS
    # --------------------------------------------------------

    final_records = []

    print(
        "\nBuilding final decisions..."
    )

    for _, row in reconciliation.iterrows():

        # ----------------------------------------------------
        # TRANSACTION ID
        # ----------------------------------------------------

        transaction_id = safe_string(
            row.get(
                "gateway_transaction_id",
                row.get(
                    "transaction_id",
                    "",
                ),
            ),
            "",
        )

        # ----------------------------------------------------
        # RECONCILIATION STATUS
        # ----------------------------------------------------

        status = safe_string(
            row.get(
                "reconciliation_status",
                "",
            ),
            "",
        )

        # ----------------------------------------------------
        # CONFIDENCE
        # ----------------------------------------------------

        confidence = safe_float(
            row.get(
                "reconciliation_confidence",
                0.0,
            )
        )

        # ----------------------------------------------------
        # EXCEPTION
        # ----------------------------------------------------

        exception = (
            exception_lookup.get(
                transaction_id,
                {},
            )
        )

        exception_type = safe_string(
            exception.get(
                "exception_type"
            )
        )

        severity = safe_string(
            exception.get(
                "severity"
            )
        )

        # ----------------------------------------------------
        # AMOUNT AT RISK
        # ----------------------------------------------------

        amount_at_risk = safe_float(
            exception.get(
                "amount_at_risk",
                0.0,
            )
        )

        # IMPORTANT:
        # If exception amount_at_risk is zero or missing,
        # use the actual reconciliation amount difference.

        amount_difference = safe_float(
            row.get(
                "amount_difference",
                exception.get(
                    "amount_difference",
                    0.0,
                ),
            )
        )

        if amount_at_risk == 0:

            amount_at_risk = abs(
                amount_difference
            )

        # ----------------------------------------------------
        # AI INVESTIGATION
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
        ai_error = None
        human_review = False

        if ai_result:

            ai_status = safe_string(
                ai_result.get(
                    "ai_status",
                ),
                "SUCCESS",
            )

            ai_confidence = safe_float(
                ai_result.get(
                    "confidence",
                    0.0,
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

            ai_error = (
                ai_result.get(
                    "ai_error"
                )
            )

            if final_decision == "RECONCILED":
                human_review = False
            else:
                human_review = True

        # ----------------------------------------------------
        # FINAL DECISION
        # ----------------------------------------------------

        final_decision, deterministic_action = (
            determine_final_decision(
                status,
                exception_type,
                severity,
                ai_result,
            )
        )

        # ----------------------------------------------------
        # SAFETY GATE
        # ----------------------------------------------------

        # AI can NEVER auto-resolve.
        #
        # Any AI-investigated exception requires
        # human review.

        if ai_result:

            human_review = True

        # ----------------------------------------------------
        # RECOMMENDED ACTION
        # ----------------------------------------------------

        recommended_action = (
            ai_action
            if ai_action
            else deterministic_action
        )

        # ----------------------------------------------------
        # FINAL RECORD
        # ----------------------------------------------------

        final_records.append(
            {
                "transaction_id":
                    transaction_id,

                "bank_reference":
                    safe_string(
                        row.get(
                            "bank_reference"
                        )
                    ),

                "reconciliation_status":
                    status,

                "reconciliation_method":
                    safe_string(
                        row.get(
                            "reconciliation_method"
                        )
                    ),

                "reconciliation_confidence":
                    confidence,

                "reconciliation_reason":
                    safe_string(
                        row.get(
                            "reconciliation_reason"
                        )
                    ),

                "exception_type":
                    exception_type,

                "severity":
                    severity,

                "amount_at_risk":
                    round(
                        amount_at_risk,
                        2,
                    ),

                "amount_difference":
                    round(
                        abs(
                            amount_difference
                        ),
                        2,
                    ),

                "reference_similarity":
                    safe_float(
                        row.get(
                            "reference_similarity",
                            0.0,
                        )
                    ),

                "merchant_similarity":
                    safe_float(
                        row.get(
                            "merchant_similarity",
                            0.0,
                        )
                    ),

                "amount_similarity":
                    safe_float(
                        row.get(
                            "amount_similarity",
                            0.0,
                        )
                    ),

                "date_similarity":
                    safe_float(
                        row.get(
                            "date_similarity",
                            0.0,
                        )
                    ),

                "candidate_count":
                    safe_float(
                        row.get(
                            "candidate_count",
                            0.0,
                        )
                    ),

                "second_best_score":
                    safe_float(
                        row.get(
                            "second_best_score",
                            0.0,
                        )
                    ),

                "score_gap":
                    safe_float(
                        row.get(
                            "score_gap",
                            0.0,
                        )
                    ),

                "ai_status":
                    ai_status,

                "ai_confidence":
                    ai_confidence,

                "ai_likely_cause":
                    ai_likely_cause,

                "ai_reasoning":
                    ai_reasoning,

                "ai_error":
                    ai_error,

                "final_decision":
                    final_decision,

                "recommended_action":
                    recommended_action,

                "requires_human_review":
                    human_review,

                # Explicit financial safety field.
                "financial_action":
                    (
                        "BLOCKED"
                        if final_decision
                        != "RECONCILED"
                        else "NONE"
                    ),
            }
        )

    return pd.DataFrame(
        final_records
    )


# ============================================================
# KPI SUMMARY
# ============================================================

def calculate_kpis(report):

    total = len(report)

    if total == 0:

        return {
            "total_transactions": 0,
            "reconciled_transactions": 0,
            "exception_transactions": 0,
            "exception_rate": 0,
            "manual_review_cases": 0,
            "investigation_cases": 0,
            "critical_exceptions": 0,
            "high_exceptions": 0,
            "medium_exceptions": 0,
            "low_exceptions": 0,
            "total_amount_at_risk": 0,
            "ai_investigated_cases": 0,
            "ai_auto_resolution": 0,
        }

    # --------------------------------------------------------
    # RECONCILED
    # --------------------------------------------------------

    reconciled = int(
        (
            report[
                "final_decision"
            ]
            == "RECONCILED"
        ).sum()
    )

    # --------------------------------------------------------
    # MANUAL REVIEW
    # --------------------------------------------------------

    manual_review = int(
        (
            report[
                "final_decision"
            ]
            == "MANUAL_REVIEW"
        ).sum()
    )

    # --------------------------------------------------------
    # INVESTIGATION
    # --------------------------------------------------------

    investigate = int(
        (
            report[
                "final_decision"
            ]
            == "INVESTIGATE"
        ).sum()
    )

    # --------------------------------------------------------
    # EXCEPTIONS
    # --------------------------------------------------------

    exceptions = (
        total - reconciled
    )

    exception_rate = (
        exceptions / total
        if total
        else 0
    )

    # --------------------------------------------------------
    # AMOUNT AT RISK
    # --------------------------------------------------------

    total_amount_at_risk = (
        report[
            "amount_at_risk"
        ]
        .fillna(0)
        .apply(
            safe_float
        )
        .sum()
    )

    # --------------------------------------------------------
    # SEVERITY
    # --------------------------------------------------------

    critical = int(
        (
            report[
                "severity"
            ]
            .fillna("")
            .astype(str)
            .str.upper()
            == "CRITICAL"
        ).sum()
    )

    high = int(
        (
            report[
                "severity"
            ]
            .fillna("")
            .astype(str)
            .str.upper()
            == "HIGH"
        ).sum()
    )

    medium = int(
        (
            report[
                "severity"
            ]
            .fillna("")
            .astype(str)
            .str.upper()
            == "MEDIUM"
        ).sum()
    )

    low = int(
        (
            report[
                "severity"
            ]
            .fillna("")
            .astype(str)
            .str.upper()
            == "LOW"
        ).sum()
    )

    # --------------------------------------------------------
    # AI CASES
    # --------------------------------------------------------

    ai_cases = int(
        report[
            "ai_status"
        ]
        .notna()
        .sum()
    )

    # --------------------------------------------------------
    # AUTO RESOLUTION
    # --------------------------------------------------------

    # ALWAYS ZERO.
    #
    # AI is investigation-only.

    ai_auto_resolution = 0

    # --------------------------------------------------------
    # RETURN
    # --------------------------------------------------------

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
                4,
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
                2,
            ),

        "ai_investigated_cases":
            ai_cases,

        "ai_auto_resolution":
            ai_auto_resolution,
    }


# ============================================================
# SAVE REPORT
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
    # CLEAN DATA
    # --------------------------------------------------------

    report = clean_dataframe_for_json(
        report
    )

    # --------------------------------------------------------
    # CSV
    # --------------------------------------------------------

    report.to_csv(
        OUTPUT_CSV,
        index=False,
    )

    # --------------------------------------------------------
    # JSON RECORDS
    # --------------------------------------------------------

    records = report.to_dict(
        orient="records"
    )

    # --------------------------------------------------------
    # JSON OUTPUT
    # --------------------------------------------------------

    output = {

        "project":
            "ReconcileAI",

        "report_type":
            "Final Reconciliation Report",

        "currency":
            "INR",

        "kpis":
            kpis,

        "pipeline": {

            "pass_1":
                "Exact Matching",

            "pass_2":
                "Fuzzy Matching",

            "pass_3":
                "AI Investigation",

            "pass_4":
                "Final Decision Engine",
        },

        "safety": {

            "ai_can_auto_resolve":
                False,

            "financial_actions_blocked":
                True,

            "human_review_required_for_exceptions":
                True,
        },

        "records":
            records,
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

    # --------------------------------------------------------
    # SEVERITY
    # --------------------------------------------------------

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

    # --------------------------------------------------------
    # DECISIONS
    # --------------------------------------------------------

    print(
        "\nDECISIONS"
    )

    print("-" * 60)

    if not report.empty:

        print(
            report[
                "final_decision"
            ]
            .value_counts()
            .to_string()
        )

    else:

        print(
            "No records."
        )

    # --------------------------------------------------------
    # AI
    # --------------------------------------------------------

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

    print(
        "Financial actions: BLOCKED"
    )

    print(
        "Human review for exceptions: REQUIRED"
    )


# ============================================================
# MAIN
# ============================================================

def main():

    try:

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

    except Exception as error:

        print(
            "\n"
            + "=" * 60
        )

        print(
            "PASS 4 FAILED"
        )

        print(
            "=" * 60
        )

        print(
            f"\nError:\n{error}"
        )

        raise


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":

    main()