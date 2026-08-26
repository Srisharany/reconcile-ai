from pathlib import Path

import pandas as pd
from rapidfuzz.fuzz import ratio


# ============================================================
# PATHS
# ============================================================

BASE_DIR = Path(__file__).resolve().parents[2]

RAW_DATA_DIR = BASE_DIR / "data" / "raw"
PROCESSED_DATA_DIR = BASE_DIR / "data" / "processed"


# ============================================================
# CONFIGURATION
# ============================================================

DATE_WINDOW_DAYS = 3
AMOUNT_TOLERANCE = 0.15

REFERENCE_WEIGHT = 0.40
MERCHANT_WEIGHT = 0.20
AMOUNT_WEIGHT = 0.25
DATE_WEIGHT = 0.15

HIGH_CONFIDENCE_THRESHOLD = 0.90
REVIEW_THRESHOLD = 0.70

MIN_REFERENCE_FOR_AUTO_MATCH = 0.80

AMBIGUITY_MARGIN = 0.05
REFERENCE_AMBIGUITY_MARGIN = 0.10

POSSIBLE_FEE_TOLERANCE = 100.00


# ============================================================
# TEXT NORMALIZATION
# ============================================================

def normalize_text(value):
    """
    Normalize text before comparison.
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


# ============================================================
# REFERENCE SIMILARITY
# ============================================================

def calculate_reference_similarity(
    gateway_reference,
    bank_reference,
):
    """
    Compare Gateway transaction ID with bank transaction
    reference.
    """

    gateway_reference = normalize_text(
        gateway_reference
    )

    bank_reference = normalize_text(
        bank_reference
    )

    if not gateway_reference or not bank_reference:
        return 0.0

    return (
        ratio(
            gateway_reference,
            bank_reference,
        )
        / 100
    )


# ============================================================
# MERCHANT SIMILARITY
# ============================================================

def calculate_merchant_similarity(
    gateway_merchant,
    bank_merchant,
):
    """
    Compare merchant names.
    """

    gateway_merchant = normalize_text(
        gateway_merchant
    )

    bank_merchant = normalize_text(
        bank_merchant
    )

    if not gateway_merchant or not bank_merchant:
        return 0.0

    return (
        ratio(
            gateway_merchant,
            bank_merchant,
        )
        / 100
    )


# ============================================================
# AMOUNT SIMILARITY
# ============================================================

def calculate_amount_similarity(
    source_amount,
    candidate_amount,
):
    """
    Convert amount difference into a 0-1 similarity score.
    """

    try:
        source_amount = float(source_amount)
        candidate_amount = float(candidate_amount)
    except (TypeError, ValueError):
        return 0.0

    if source_amount == candidate_amount:
        return 1.0

    if source_amount <= 0:
        return 0.0

    difference = abs(
        source_amount - candidate_amount
    )

    percentage_difference = (
        difference / source_amount
    )

    return max(
        0.0,
        1.0 - percentage_difference,
    )


# ============================================================
# AMOUNT DIFFERENCE
# ============================================================

def calculate_amount_difference(
    source_amount,
    candidate_amount,
):
    """
    Calculate absolute monetary difference.
    """

    try:
        return round(
            abs(
                float(source_amount)
                - float(candidate_amount)
            ),
            2,
        )
    except (TypeError, ValueError):
        return None


# ============================================================
# DATE SIMILARITY
# ============================================================

def calculate_date_similarity(
    source_date,
    candidate_date,
):
    """
    Calculate settlement-date proximity.

    Same day = 1.00
    +1 day   = 0.75
    +2 days  = 0.50
    +3 days  = 0.25
    >3 days  = 0.00
    """

    try:
        source_date = pd.to_datetime(source_date)
        candidate_date = pd.to_datetime(candidate_date)
    except Exception:
        return 0.0

    difference = abs(
        (source_date - candidate_date).days
    )

    if difference == 0:
        return 1.0

    if difference == 1:
        return 0.75

    if difference == 2:
        return 0.50

    if difference == 3:
        return 0.25

    return 0.0


# ============================================================
# CANDIDATE GENERATION
# ============================================================

def generate_candidates(
    gateway_transaction,
    bank,
):
    """
    Generate plausible bank candidates.

    Blocking rules:

    1. Same currency
    2. Settlement within +/- 3 days
    3. Amount within +/- 15%
    """

    gateway_date = pd.to_datetime(
        gateway_transaction["transaction_date"]
    )

    gateway_amount = float(
        gateway_transaction["amount"]
    )

    gateway_currency = (
        gateway_transaction["currency"]
    )

    bank_dates = pd.to_datetime(
        bank["settlement_date"]
    )

    date_difference = (
        bank_dates - gateway_date
    ).abs().dt.days

    amount_difference = (
        bank["credit_amount"]
        - gateway_amount
    ).abs()

    amount_limit = max(
        gateway_amount * AMOUNT_TOLERANCE,
        100,
    )

    candidates = bank[
        (
            bank["currency"]
            == gateway_currency
        )
        &
        (
            date_difference
            <= DATE_WINDOW_DAYS
        )
        &
        (
            amount_difference
            <= amount_limit
        )
    ].copy()

    return candidates


# ============================================================
# SCORE CANDIDATE
# ============================================================

def score_candidate(
    gateway_transaction,
    bank_transaction,
):
    """
    Calculate weighted similarity score.

    Reference = 40%
    Merchant  = 20%
    Amount    = 25%
    Date      = 15%
    """

    reference_similarity = (
        calculate_reference_similarity(
            gateway_transaction[
                "gateway_transaction_id"
            ],
            bank_transaction[
                "transaction_reference"
            ],
        )
    )

    merchant_similarity = (
        calculate_merchant_similarity(
            gateway_transaction[
                "merchant_name"
            ],
            bank_transaction[
                "merchant_name"
            ],
        )
    )

    amount_similarity = (
        calculate_amount_similarity(
            gateway_transaction["amount"],
            bank_transaction["credit_amount"],
        )
    )

    date_similarity = (
        calculate_date_similarity(
            gateway_transaction[
                "transaction_date"
            ],
            bank_transaction[
                "settlement_date"
            ],
        )
    )

    amount_difference = (
        calculate_amount_difference(
            gateway_transaction["amount"],
            bank_transaction["credit_amount"],
        )
    )

    final_score = (
        reference_similarity
        * REFERENCE_WEIGHT
        +
        merchant_similarity
        * MERCHANT_WEIGHT
        +
        amount_similarity
        * AMOUNT_WEIGHT
        +
        date_similarity
        * DATE_WEIGHT
    )

    return {
        "reference_similarity": round(
            reference_similarity,
            4,
        ),
        "merchant_similarity": round(
            merchant_similarity,
            4,
        ),
        "amount_similarity": round(
            amount_similarity,
            4,
        ),
        "date_similarity": round(
            date_similarity,
            4,
        ),
        "amount_difference": amount_difference,
        "final_score": round(
            final_score,
            4,
        ),
    }


# ============================================================
# DECISION ENGINE
# ============================================================

def make_decision(
    best,
    second_best,
    candidate_count,
):
    """
    Convert similarity scores into a reconciliation decision.
    """

    score = best["final_score"]

    reference_similarity = (
        best["reference_similarity"]
    )

    amount_difference = (
        best["amount_difference"]
    )

    # --------------------------------------------------------
    # No candidate
    # --------------------------------------------------------

    if candidate_count == 0:

        return {
            "status": "MISSING_SETTLEMENT",
            "method": "FUZZY",
            "confidence": 0.0,
            "reason": (
                "No plausible bank settlement "
                "was found within the configured "
                "date and amount windows."
            ),
            "recommended_action": (
                "Investigate missing settlement."
            ),
        }

    # --------------------------------------------------------
    # EXACT REFERENCE OVERRIDE
    # --------------------------------------------------------

    if (
        reference_similarity == 1.0
        and amount_difference == 0
        and best["merchant_similarity"] >= 0.95
        and score >= 0.90
    ):

        return {
            "status": "MATCHED",
            "method": "FUZZY_EXACT_REFERENCE",
            "confidence": score,
            "reason": (
                "Exact transaction reference with "
                "matching amount and highly similar "
                "merchant."
            ),
            "recommended_action": (
                "Auto-reconcile."
            ),
        }

    # --------------------------------------------------------
    # AMBIGUITY CHECK
    # --------------------------------------------------------

    if second_best is not None:

        score_gap = (
            best["final_score"]
            - second_best["final_score"]
        )

        reference_gap = abs(
            best["reference_similarity"]
            - second_best["reference_similarity"]
        )

        references_are_similar = (
            reference_gap
            < REFERENCE_AMBIGUITY_MARGIN
        )

        if (
            score_gap < AMBIGUITY_MARGIN
            and references_are_similar
        ):

            return {
                "status": "AMBIGUOUS",
                "method": "FUZZY",
                "confidence": score,
                "reason": (
                    "Multiple bank candidates have "
                    "similar overall scores and "
                    "similar transaction-reference "
                    "similarity."
                ),
                "recommended_action": (
                    "Send to AI or manual investigation."
                ),
            }

    # --------------------------------------------------------
    # WEAK REFERENCE PROTECTION
    # --------------------------------------------------------

    if (
        score >= HIGH_CONFIDENCE_THRESHOLD
        and reference_similarity
        < MIN_REFERENCE_FOR_AUTO_MATCH
    ):

        return {
            "status": "AMBIGUOUS",
            "method": "FUZZY_WEAK_REFERENCE",
            "confidence": score,
            "reason": (
                "Overall similarity is high, but "
                "transaction-reference similarity "
                "is too weak for automatic matching."
            ),
            "recommended_action": (
                "Require additional investigation."
            ),
        }

    # --------------------------------------------------------
    # EXACT AMOUNT
    # --------------------------------------------------------

    if (
        score >= HIGH_CONFIDENCE_THRESHOLD
        and amount_difference == 0
    ):

        return {
            "status": "MATCHED",
            "method": "FUZZY_HIGH_CONFIDENCE",
            "confidence": score,
            "reason": (
                "Strong transaction-reference, "
                "merchant, amount and date agreement."
            ),
            "recommended_action": (
                "Auto-reconcile."
            ),
        }

    # --------------------------------------------------------
    # POSSIBLE FEE / SMALL VARIANCE
    # --------------------------------------------------------

    if (
        score >= HIGH_CONFIDENCE_THRESHOLD
        and amount_difference is not None
        and amount_difference
        <= POSSIBLE_FEE_TOLERANCE
    ):

        return {
            "status": "MATCHED_WITH_FEE",
            "method": "FUZZY_AMOUNT_VARIANCE",
            "confidence": score,
            "reason": (
                f"Strong transaction identity match "
                f"with a ₹{amount_difference:.2f} "
                f"settlement difference. This may "
                f"represent a fee or adjustment."
            ),
            "recommended_action": (
                "Investigate the amount variance "
                "before final reconciliation."
            ),
        }

    # --------------------------------------------------------
    # LARGE AMOUNT MISMATCH
    # --------------------------------------------------------

    if (
        score >= HIGH_CONFIDENCE_THRESHOLD
    ):

        return {
            "status": "MATCHED_WITH_AMOUNT_MISMATCH",
            "method": "FUZZY_AMOUNT_MISMATCH",
            "confidence": score,
            "reason": (
                f"Strong transaction identity match "
                f"but settlement amount differs by "
                f"₹{amount_difference:.2f}."
            ),
            "recommended_action": (
                "Investigate fee, refund, adjustment "
                "or partial settlement."
            ),
        }

    # --------------------------------------------------------
    # REVIEW
    # --------------------------------------------------------

    if score >= REVIEW_THRESHOLD:

        return {
            "status": "REVIEW",
            "method": "FUZZY_REVIEW",
            "confidence": score,
            "reason": (
                "Candidate has moderate similarity "
                "but does not meet automatic "
                "reconciliation criteria."
            ),
            "recommended_action": (
                "Send to AI or manual review."
            ),
        }

    # --------------------------------------------------------
    # UNRESOLVED
    # --------------------------------------------------------

    return {
        "status": "UNRESOLVED",
        "method": "FUZZY_LOW_CONFIDENCE",
        "confidence": score,
        "reason": (
            "No sufficiently reliable bank "
            "candidate was identified."
        ),
        "recommended_action": (
            "Keep unresolved and investigate."
        ),
    }


# ============================================================
# MATCH ONE TRANSACTION
# ============================================================

def fuzzy_match_transaction(
    gateway_transaction,
    bank,
):
    """
    Match one gateway transaction to the best bank candidate.
    """

    candidates = generate_candidates(
        gateway_transaction,
        bank,
    )

    # --------------------------------------------------------
    # No candidates
    # --------------------------------------------------------

    if candidates.empty:

        decision = make_decision(
            {
                "final_score": 0.0,
                "reference_similarity": 0.0,
                "merchant_similarity": 0.0,
                "amount_similarity": 0.0,
                "date_similarity": 0.0,
                "amount_difference": None,
            },
            None,
            0,
        )

        return {
            "gateway_transaction_id": (
                gateway_transaction[
                    "gateway_transaction_id"
                ]
            ),
            "bank_reference": None,
            "fuzzy_status": decision["status"],
            "fuzzy_method": decision["method"],
            "fuzzy_confidence": decision["confidence"],
            "reference_similarity": 0.0,
            "merchant_similarity": 0.0,
            "amount_similarity": 0.0,
            "date_similarity": 0.0,
            "amount_difference": None,
            "candidate_count": 0,
            "second_best_score": None,
            "score_gap": None,
            "reason": decision["reason"],
            "recommended_action": (
                decision["recommended_action"]
            ),
        }

    # --------------------------------------------------------
    # Score candidates
    # --------------------------------------------------------

    scored_candidates = []

    for _, bank_transaction in (
        candidates.iterrows()
    ):

        score = score_candidate(
            gateway_transaction,
            bank_transaction,
        )

        scored_candidates.append(
            {
                "bank_index": bank_transaction.name,
                **score,
            }
        )

    scored_candidates.sort(
        key=lambda item: item["final_score"],
        reverse=True,
    )

    best = scored_candidates[0]

    second_best = None

    if len(scored_candidates) > 1:
        second_best = scored_candidates[1]

    best_bank = bank.loc[
        best["bank_index"]
    ]

    # --------------------------------------------------------
    # Decision
    # --------------------------------------------------------

    decision = make_decision(
        best,
        second_best,
        len(candidates),
    )

    # --------------------------------------------------------
    # Score gap
    # --------------------------------------------------------

    if second_best is not None:

        second_best_score = (
            second_best["final_score"]
        )

        score_gap = round(
            best["final_score"]
            - second_best_score,
            4,
        )

    else:

        second_best_score = None
        score_gap = None

    # --------------------------------------------------------
    # Return
    # --------------------------------------------------------

    return {
        "gateway_transaction_id": (
            gateway_transaction[
                "gateway_transaction_id"
            ]
        ),
        "bank_reference": (
            best_bank["bank_reference"]
        ),
        "fuzzy_status": decision["status"],
        "fuzzy_method": decision["method"],
        "fuzzy_confidence": decision["confidence"],
        "reference_similarity": (
            best["reference_similarity"]
        ),
        "merchant_similarity": (
            best["merchant_similarity"]
        ),
        "amount_similarity": (
            best["amount_similarity"]
        ),
        "date_similarity": (
            best["date_similarity"]
        ),
        "amount_difference": (
            best["amount_difference"]
        ),
        "candidate_count": len(candidates),
        "second_best_score": second_best_score,
        "score_gap": score_gap,
        "reason": decision["reason"],
        "recommended_action": (
            decision["recommended_action"]
        ),
    }


# ============================================================
# RUN FUZZY MATCHING
# ============================================================

def run_fuzzy_matching(
    gateway,
    bank,
):
    """
    Run fuzzy matching across supplied gateway transactions.
    """

    results = []

    for _, gateway_transaction in (
        gateway.iterrows()
    ):

        result = fuzzy_match_transaction(
            gateway_transaction,
            bank,
        )

        results.append(result)

    return pd.DataFrame(results)


# ============================================================
# MAIN
# ============================================================

def main():

    print("=" * 60)
    print(
        "ReconcileAI — Pass 2 V2: "
        "Explainable Fuzzy Matching"
    )
    print("=" * 60)

    gateway = pd.read_csv(
        RAW_DATA_DIR
        / "gateway_transactions.csv"
    )

    bank = pd.read_csv(
        RAW_DATA_DIR
        / "bank_statements.csv"
    )

    print("\nDATASET")

    print(
        f"Gateway transactions: {len(gateway)}"
    )

    print(
        f"Bank statements:      {len(bank)}"
    )

    print(
        "\nRunning fuzzy candidate matching..."
    )

    results = run_fuzzy_matching(
        gateway,
        bank,
    )

    print("\n" + "=" * 60)
    print("FUZZY V2 SUMMARY")
    print("=" * 60)

    print(
        results[
            "fuzzy_status"
        ]
        .value_counts()
        .to_string()
    )

    print(
        "\nAverage candidates evaluated:"
    )

    print(
        f"{results['candidate_count'].mean():.2f}"
    )

    print(
        "\nAverage confidence:"
    )

    print(
        f"{results['fuzzy_confidence'].mean():.2%}"
    )

    PROCESSED_DATA_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    output_file = (
        PROCESSED_DATA_DIR
        / "fuzzy_v2_results.csv"
    )

    results.to_csv(
        output_file,
        index=False,
    )

    print(
        f"\nResults saved to:\n"
        f"{output_file}"
    )

    print(
        "\nPass 2 V2 complete."
    )


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":
    main()