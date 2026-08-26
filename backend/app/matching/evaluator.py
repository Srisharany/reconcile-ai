from pathlib import Path

import pandas as pd


# ============================================================
# PATHS
# ============================================================

BASE_DIR = Path(__file__).resolve().parents[2]

GROUND_TRUTH_FILE = (
    BASE_DIR
    / "data"
    / "ground_truth"
    / "ground_truth.csv"
)

FUZZY_RESULTS_FILE = (
    BASE_DIR
    / "data"
    / "processed"
    / "fuzzy_reconciliation_results.csv"
)

OUTPUT_DIR = (
    BASE_DIR
    / "data"
    / "processed"
)


# ============================================================
# LOAD DATA
# ============================================================

def load_data():
    """
    Load ground truth and fuzzy predictions.
    """

    ground_truth = pd.read_csv(
        GROUND_TRUTH_FILE
    )

    predictions = pd.read_csv(
        FUZZY_RESULTS_FILE
    )

    return ground_truth, predictions


# ============================================================
# PREPARE GROUND TRUTH
# ============================================================

def prepare_ground_truth(ground_truth):
    """
    Prepare ground truth for Gateway → Bank evaluation.

    A transaction has an expected bank match when
    expected_bank_match is True and bank_reference exists.
    """

    ground_truth = ground_truth.copy()

    ground_truth["expected_bank_match"] = (
        ground_truth["expected_bank_match"]
        .fillna(False)
        .astype(bool)
    )

    ground_truth["has_expected_bank_match"] = (
        ground_truth["expected_bank_match"]
        & ground_truth["bank_reference"].notna()
    )

    return ground_truth


# ============================================================
# MERGE PREDICTIONS WITH GROUND TRUTH
# ============================================================

def merge_predictions_with_truth(
    ground_truth,
    predictions,
):
    """
    Join predictions with the original transaction truth.
    """

    evaluation = ground_truth.merge(
        predictions,
        left_on="transaction_id",
        right_on="gateway_transaction_id",
        how="left",
    )

    return evaluation


# ============================================================
# NORMALIZE REFERENCES
# ============================================================

def normalize_reference(value):
    """
    Normalize references before comparison.
    """

    if pd.isna(value):
        return None

    return (
        str(value)
        .strip()
        .upper()
    )


# ============================================================
# EVALUATE PREDICTIONS
# ============================================================

def evaluate_predictions(evaluation):
    """
    Determine whether each prediction is:

        TRUE POSITIVE
        FALSE POSITIVE
        FALSE NEGATIVE
        TRUE NEGATIVE
    """

    evaluation = evaluation.copy()

    evaluation["predicted_bank_reference"] = (
        evaluation["bank_reference_y"]
        .apply(normalize_reference)
    )

    evaluation["actual_bank_reference"] = (
        evaluation["bank_reference_x"]
        .apply(normalize_reference)
    )

    evaluation["predicted_match"] = (
        evaluation["fuzzy_status"]
        == "MATCHED"
    )

    evaluation["actual_match"] = (
        evaluation["has_expected_bank_match"]
    )

    evaluation["correct_match"] = (
        evaluation["predicted_match"]
        & evaluation["actual_match"]
        & (
            evaluation["predicted_bank_reference"]
            == evaluation["actual_bank_reference"]
        )
    )

    evaluation["false_match"] = (
        evaluation["predicted_match"]
        & ~evaluation["correct_match"]
    )

    evaluation["missed_match"] = (
        ~evaluation["predicted_match"]
        & evaluation["actual_match"]
    )

    evaluation["correct_unmatched"] = (
        ~evaluation["predicted_match"]
        & ~evaluation["actual_match"]
    )

    return evaluation


# ============================================================
# CALCULATE METRICS
# ============================================================

def calculate_metrics(evaluation):
    """
    Calculate precision, recall and F1 score.
    """

    true_positive = int(
        evaluation["correct_match"].sum()
    )

    false_positive = int(
        evaluation["false_match"].sum()
    )

    false_negative = int(
        evaluation["missed_match"].sum()
    )

    true_negative = int(
        evaluation["correct_unmatched"].sum()
    )

    # Precision
    if true_positive + false_positive > 0:
        precision = (
            true_positive
            / (true_positive + false_positive)
        )
    else:
        precision = 0.0

    # Recall
    if true_positive + false_negative > 0:
        recall = (
            true_positive
            / (true_positive + false_negative)
        )
    else:
        recall = 0.0

    # F1
    if precision + recall > 0:
        f1 = (
            2
            * precision
            * recall
            / (precision + recall)
        )
    else:
        f1 = 0.0

    return {
        "true_positive": true_positive,
        "false_positive": false_positive,
        "false_negative": false_negative,
        "true_negative": true_negative,
        "precision": precision,
        "recall": recall,
        "f1_score": f1,
    }


# ============================================================
# PRINT METRICS
# ============================================================

def print_metrics(metrics):
    """
    Print evaluation metrics.
    """

    print("\n" + "=" * 60)
    print("RECONCILIATION EVALUATION")
    print("=" * 60)

    print(
        f"\nTrue Positives:  "
        f"{metrics['true_positive']}"
    )

    print(
        f"False Positives: "
        f"{metrics['false_positive']}"
    )

    print(
        f"False Negatives: "
        f"{metrics['false_negative']}"
    )

    print(
        f"True Negatives:  "
        f"{metrics['true_negative']}"
    )

    print(
        f"\nPrecision: "
        f"{metrics['precision']:.2%}"
    )

    print(
        f"Recall:    "
        f"{metrics['recall']:.2%}"
    )

    print(
        f"F1 Score:  "
        f"{metrics['f1_score']:.2%}"
    )


# ============================================================
# ERROR ANALYSIS
# ============================================================

def print_error_analysis(evaluation):
    """
    Show examples of incorrect predictions.
    """

    false_matches = evaluation[
        evaluation["false_match"]
    ]

    missed_matches = evaluation[
        evaluation["missed_match"]
    ]

    print("\n" + "=" * 60)
    print("ERROR ANALYSIS")
    print("=" * 60)

    print(
        f"\nFalse matches: "
        f"{len(false_matches)}"
    )

    if not false_matches.empty:

        columns = [
            "transaction_id",
            "actual_bank_reference",
            "predicted_bank_reference",
            "fuzzy_confidence",
            "fuzzy_status",
        ]

        print(
            false_matches[
                columns
            ]
            .head(10)
            .to_string(index=False)
        )

    print(
        f"\nMissed matches: "
        f"{len(missed_matches)}"
    )

    if not missed_matches.empty:

        columns = [
            "transaction_id",
            "actual_bank_reference",
            "fuzzy_confidence",
            "fuzzy_status",
        ]

        print(
            missed_matches[
                columns
            ]
            .head(10)
            .to_string(index=False)
        )


# ============================================================
# SAVE EVALUATION
# ============================================================

def save_evaluation(evaluation):
    """
    Save transaction-level evaluation results.
    """

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    output_file = (
        OUTPUT_DIR
        / "fuzzy_evaluation.csv"
    )

    evaluation.to_csv(
        output_file,
        index=False,
    )

    return output_file


# ============================================================
# MAIN
# ============================================================

def main():

    print("=" * 60)
    print("ReconcileAI — Fuzzy Matching Evaluation")
    print("=" * 60)

    print("\nLoading evaluation data...")

    ground_truth, predictions = load_data()

    print(
        f"Ground truth records: "
        f"{len(ground_truth)}"
    )

    print(
        f"Prediction records: "
        f"{len(predictions)}"
    )

    print("\nPreparing ground truth...")

    ground_truth = prepare_ground_truth(
        ground_truth
    )

    print("Merging predictions with truth...")

    evaluation = merge_predictions_with_truth(
        ground_truth,
        predictions,
    )

    print("Evaluating predictions...")

    evaluation = evaluate_predictions(
        evaluation
    )

    metrics = calculate_metrics(
        evaluation
    )

    print_metrics(metrics)

    print_error_analysis(
        evaluation
    )

    output_file = save_evaluation(
        evaluation
    )

    print(
        f"\nDetailed evaluation saved to:"
        f"\n{output_file}"
    )

    print("\nEvaluation complete.")


if __name__ == "__main__":
    main()