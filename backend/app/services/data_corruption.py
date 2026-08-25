import random
from pathlib import Path

import pandas as pd


# ---------------------------------------------------------
# Configuration
# ---------------------------------------------------------

RANDOM_SEED = 42

MISSING_GATEWAY_RATE = 0.05
MISSING_BANK_RATE = 0.08
DUPLICATE_RATE = 0.03
AMOUNT_MISMATCH_RATE = 0.05
REFERENCE_TYPO_RATE = 0.05
MERCHANT_TYPO_RATE = 0.05
BANK_FEE_RATE = 0.05


# ---------------------------------------------------------
# Paths
# ---------------------------------------------------------

BASE_DIR = Path(__file__).resolve().parents[2]

DATA_DIR = BASE_DIR / "data"

RAW_DIR = DATA_DIR / "raw"
GROUND_TRUTH_DIR = DATA_DIR / "ground_truth"


# ---------------------------------------------------------
# Utility functions
# ---------------------------------------------------------

def introduce_reference_typo(reference: str) -> str:
    """
    Introduce a small typo into a transaction reference.
    """

    if not reference:
        return reference

    reference = str(reference)

    position = random.randint(0, len(reference) - 1)

    characters = list(reference)

    replacement_characters = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"

    characters[position] = random.choice(replacement_characters)

    return "".join(characters)


def introduce_merchant_typo(merchant: str) -> str:
    """
    Introduce a realistic merchant-name typo.
    """

    if not merchant:
        return merchant

    merchant = str(merchant)

    typo_variations = {
        "Stores": "Store",
        "Store": "Stores",
        "Electronics": "Electronic",
        "Fashion": "Fashon",
        "Grocery": "Groccery",
        "Daily": "Daly",
        "Smart": "Smaart",
        "Tech": "Tek",
        "Fresh": "Fres",
    }

    for original, replacement in typo_variations.items():
        if original in merchant:
            return merchant.replace(original, replacement, 1)

    # Generic fallback: remove one character
    if len(merchant) > 5:
        position = random.randint(1, len(merchant) - 2)

        return (
            merchant[:position]
            + merchant[position + 1:]
        )

    return merchant


# ---------------------------------------------------------
# Ground truth
# ---------------------------------------------------------

def create_ground_truth(
    orders: pd.DataFrame,
    gateway: pd.DataFrame,
    bank: pd.DataFrame,
) -> pd.DataFrame:
    """
    Create the original relationship between all three sources.

    This file is ONLY used for evaluation.
    The reconciliation engine must never use it.
    """

    ground_truth = pd.DataFrame(
        {
            "transaction_id": gateway["gateway_transaction_id"],
            "order_id": gateway["order_reference"],
            "original_amount": gateway["amount"],
            "currency": gateway["currency"],
            "merchant_name": gateway["merchant_name"],
            "transaction_date": gateway["transaction_date"],
        }
    )

    # Map each gateway transaction to its corresponding bank record.
    bank_mapping = dict(
        zip(
            bank["transaction_reference"],
            bank["bank_reference"],
        )
    )

    ground_truth["bank_reference"] = (
        ground_truth["transaction_id"].map(bank_mapping)
    )

    ground_truth["expected_order_match"] = True
    ground_truth["expected_gateway_match"] = True
    ground_truth["expected_bank_match"] = (
        ground_truth["bank_reference"].notna()
    )

    return ground_truth


# ---------------------------------------------------------
# Missing records
# ---------------------------------------------------------

def remove_random_records(
    dataframe: pd.DataFrame,
    rate: float,
) -> tuple[pd.DataFrame, list]:
    """
    Randomly remove records from a dataset.

    Returns:
        modified dataframe
        list of removed identifiers
    """

    dataframe = dataframe.copy()

    remove_count = int(len(dataframe) * rate)

    if remove_count == 0:
        return dataframe, []

    indexes = random.sample(
        list(dataframe.index),
        remove_count,
    )

    removed = dataframe.loc[indexes].copy()

    dataframe = dataframe.drop(indexes)

    return dataframe.reset_index(drop=True), removed


# ---------------------------------------------------------
# Amount mismatches
# ---------------------------------------------------------

def introduce_amount_mismatches(
    bank: pd.DataFrame,
    rate: float,
) -> tuple[pd.DataFrame, list]:
    """
    Modify bank settlement amounts.

    This simulates:
    - settlement adjustments
    - small deductions
    - reconciliation differences
    """

    bank = bank.copy()

    count = int(len(bank) * rate)

    if count == 0:
        return bank, []

    indexes = random.sample(
        list(bank.index),
        count,
    )

    changes = []

    for index in indexes:

        original_amount = float(
            bank.at[index, "credit_amount"]
        )

        difference = round(
            random.uniform(1, min(100, original_amount * 0.05)),
            2,
        )

        new_amount = round(
            original_amount - difference,
            2,
        )

        bank.at[index, "credit_amount"] = new_amount

        changes.append(
            {
                "transaction_id": bank.at[
                    index,
                    "transaction_reference",
                ],
                "corruption_type": "AMOUNT_MISMATCH",
                "original_value": original_amount,
                "corrupted_value": new_amount,
                "difference": difference,
            }
        )

    return bank, changes


# ---------------------------------------------------------
# Reference typos
# ---------------------------------------------------------

def introduce_reference_typos(
    bank: pd.DataFrame,
    rate: float,
) -> tuple[pd.DataFrame, list]:
    """
    Introduce typos into bank transaction references.
    """

    bank = bank.copy()

    count = int(len(bank) * rate)

    if count == 0:
        return bank, []

    indexes = random.sample(
        list(bank.index),
        count,
    )

    changes = []

    for index in indexes:

        original = bank.at[
            index,
            "transaction_reference",
        ]

        corrupted = introduce_reference_typo(original)

        bank.at[
            index,
            "transaction_reference",
        ] = corrupted

        changes.append(
            {
                "transaction_id": original,
                "corruption_type": "REFERENCE_TYPO",
                "original_value": original,
                "corrupted_value": corrupted,
            }
        )

    return bank, changes


# ---------------------------------------------------------
# Merchant name typos
# ---------------------------------------------------------

def introduce_merchant_typos(
    bank: pd.DataFrame,
    rate: float,
) -> tuple[pd.DataFrame, list]:
    """
    Introduce merchant-name inconsistencies.
    """

    bank = bank.copy()

    count = int(len(bank) * rate)

    if count == 0:
        return bank, []

    indexes = random.sample(
        list(bank.index),
        count,
    )

    changes = []

    for index in indexes:

        original = bank.at[
            index,
            "merchant_name",
        ]

        corrupted = introduce_merchant_typo(original)

        bank.at[
            index,
            "merchant_name",
        ] = corrupted

        changes.append(
            {
                "transaction_id": bank.at[
                    index,
                    "transaction_reference",
                ],
                "corruption_type": "MERCHANT_TYPO",
                "original_value": original,
                "corrupted_value": corrupted,
            }
        )

    return bank, changes


# ---------------------------------------------------------
# Duplicate records
# ---------------------------------------------------------

def introduce_duplicates(
    dataframe: pd.DataFrame,
    rate: float,
) -> tuple[pd.DataFrame, list]:
    """
    Duplicate a small number of records.
    """

    dataframe = dataframe.copy()

    count = int(len(dataframe) * rate)

    if count == 0:
        return dataframe, []

    indexes = random.sample(
        list(dataframe.index),
        count,
    )

    duplicates = dataframe.loc[indexes].copy()

    dataframe = pd.concat(
        [
            dataframe,
            duplicates,
        ],
        ignore_index=True,
    )

    duplicate_ids = []

    for index in indexes:
        if "transaction_reference" in dataframe.columns:
            duplicate_ids.append(
                dataframe.loc[
                    index,
                    "transaction_reference",
                ]
            )

        elif "gateway_transaction_id" in dataframe.columns:
            duplicate_ids.append(
                dataframe.loc[
                    index,
                    "gateway_transaction_id",
                ]
            )

        elif "order_id" in dataframe.columns:
            duplicate_ids.append(
                dataframe.loc[
                    index,
                    "order_id",
                ]
            )

    return dataframe, duplicate_ids


# ---------------------------------------------------------
# Main corruption pipeline
# ---------------------------------------------------------

def corrupt_datasets(
    orders: pd.DataFrame,
    gateway: pd.DataFrame,
    bank: pd.DataFrame,
):
    """
    Apply realistic financial-data corruption.

    Returns:
        corrupted orders
        corrupted gateway
        corrupted bank
        corruption log
    """

    random.seed(RANDOM_SEED)

    corruption_log = []

    # -----------------------------------------------------
    # 1. Remove gateway records
    # -----------------------------------------------------

    gateway, removed_gateway = remove_random_records(
        gateway,
        MISSING_GATEWAY_RATE,
    )

    for _, row in removed_gateway.iterrows():

        corruption_log.append(
            {
                "transaction_id": row[
                    "gateway_transaction_id"
                ],
                "corruption_type": "MISSING_GATEWAY_RECORD",
                "original_value": "PRESENT",
                "corrupted_value": "MISSING",
            }
        )

    # -----------------------------------------------------
    # 2. Remove bank records
    # -----------------------------------------------------

    bank, removed_bank = remove_random_records(
        bank,
        MISSING_BANK_RATE,
    )

    for _, row in removed_bank.iterrows():

        corruption_log.append(
            {
                "transaction_id": row[
                    "transaction_reference"
                ],
                "corruption_type": "MISSING_BANK_RECORD",
                "original_value": "PRESENT",
                "corrupted_value": "MISSING",
            }
        )

    # -----------------------------------------------------
    # 3. Amount mismatches
    # -----------------------------------------------------

    bank, amount_changes = introduce_amount_mismatches(
        bank,
        AMOUNT_MISMATCH_RATE,
    )

    corruption_log.extend(amount_changes)

    # -----------------------------------------------------
    # 4. Reference typos
    # -----------------------------------------------------

    bank, reference_changes = introduce_reference_typos(
        bank,
        REFERENCE_TYPO_RATE,
    )

    corruption_log.extend(reference_changes)

    # -----------------------------------------------------
    # 5. Merchant typos
    # -----------------------------------------------------

    bank, merchant_changes = introduce_merchant_typos(
        bank,
        MERCHANT_TYPO_RATE,
    )

    corruption_log.extend(merchant_changes)

    # -----------------------------------------------------
    # 6. Duplicate bank records
    # -----------------------------------------------------

    bank, duplicate_ids = introduce_duplicates(
        bank,
        DUPLICATE_RATE,
    )

    for transaction_id in duplicate_ids:

        corruption_log.append(
            {
                "transaction_id": transaction_id,
                "corruption_type": "DUPLICATE_RECORD",
                "original_value": "ONE_RECORD",
                "corrupted_value": "DUPLICATED",
            }
        )

    corruption_log = pd.DataFrame(corruption_log)

    return (
        orders.reset_index(drop=True),
        gateway.reset_index(drop=True),
        bank.reset_index(drop=True),
        corruption_log,
    )


# ---------------------------------------------------------
# Save datasets
# ---------------------------------------------------------

def save_datasets(
    orders: pd.DataFrame,
    gateway: pd.DataFrame,
    bank: pd.DataFrame,
    ground_truth: pd.DataFrame,
    corruption_log: pd.DataFrame,
):
    """
    Save generated datasets to the project data directory.
    """

    RAW_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    GROUND_TRUTH_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    orders.to_csv(
        RAW_DIR / "orders.csv",
        index=False,
    )

    gateway.to_csv(
        RAW_DIR / "gateway_transactions.csv",
        index=False,
    )

    bank.to_csv(
        RAW_DIR / "bank_statements.csv",
        index=False,
    )

    ground_truth.to_csv(
        GROUND_TRUTH_DIR / "ground_truth.csv",
        index=False,
    )

    corruption_log.to_csv(
        GROUND_TRUTH_DIR / "corruption_log.csv",
        index=False,
    )


# ---------------------------------------------------------
# Run
# ---------------------------------------------------------

def main():
    """
    Generate clean data, create ground truth,
    inject corruption and save everything.
    """

    print("=" * 60)
    print("ReconcileAI - Synthetic Financial Data Generator")
    print("=" * 60)

    # Generate clean master data
    from app.services.data_generator import generate_dataset

    orders, gateway, bank = generate_dataset(1000)

    print("\nCLEAN DATA")
    print("-" * 60)

    print(f"Orders:              {len(orders)}")
    print(f"Gateway transactions: {len(gateway)}")
    print(f"Bank statements:      {len(bank)}")

    # Create ground truth BEFORE corruption
    ground_truth = create_ground_truth(
        orders,
        gateway,
        bank,
    )

    # Corrupt the datasets
    (
        corrupted_orders,
        corrupted_gateway,
        corrupted_bank,
        corruption_log,
    ) = corrupt_datasets(
        orders,
        gateway,
        bank,
    )

    # Save
    save_datasets(
        corrupted_orders,
        corrupted_gateway,
        corrupted_bank,
        ground_truth,
        corruption_log,
    )

    print("\nMESSY DATA")
    print("-" * 60)

    print(
        f"Orders:              "
        f"{len(corrupted_orders)}"
    )

    print(
        f"Gateway transactions: "
        f"{len(corrupted_gateway)}"
    )

    print(
        f"Bank statements:      "
        f"{len(corrupted_bank)}"
    )

    print("\nCORRUPTION SUMMARY")
    print("-" * 60)

    if not corruption_log.empty:

        summary = (
            corruption_log[
                "corruption_type"
            ]
            .value_counts()
        )

        for corruption_type, count in summary.items():

            print(
                f"{corruption_type:<30} "
                f"{count}"
            )

    print("\nFILES CREATED")
    print("-" * 60)

    print(
        f"Orders:          "
        f"{RAW_DIR / 'orders.csv'}"
    )

    print(
        f"Gateway:         "
        f"{RAW_DIR / 'gateway_transactions.csv'}"
    )

    print(
        f"Bank:            "
        f"{RAW_DIR / 'bank_statements.csv'}"
    )

    print(
        f"Ground truth:    "
        f"{GROUND_TRUTH_DIR / 'ground_truth.csv'}"
    )

    print(
        f"Corruption log:  "
        f"{GROUND_TRUTH_DIR / 'corruption_log.csv'}"
    )

    print("\nData generation complete.")


if __name__ == "__main__":
    main()