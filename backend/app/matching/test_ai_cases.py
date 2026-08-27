import json

from app.matching.ai_investigator import (
    investigate_exception,
)


EVIDENCE_FILE = (
    "data/processed/evidence_packages.json"
)


TARGET_TYPES = {
    "DUPLICATE_TRANSACTION",
    "POSSIBLE_FEE",
    "AMOUNT_MISMATCH",
}


def main():

    with open(
        EVIDENCE_FILE,
        "r",
        encoding="utf-8"
    ) as file:

        packages = json.load(file)

    selected = {}

    for package in packages:

        exception_type = (
            package[
                "exception"
            ][
                "exception_type"
            ]
        )

        if (
            exception_type
            in TARGET_TYPES
            and exception_type
            not in selected
        ):

            selected[
                exception_type
            ] = package

    print("=" * 60)
    print(
        "ReconcileAI — Pass 3 V2 Test"
    )
    print("=" * 60)

    for exception_type in TARGET_TYPES:

        package = selected.get(
            exception_type
        )

        if package is None:

            print(
                f"\nNo case found for "
                f"{exception_type}"
            )

            continue

        print(
            f"\n\n{'=' * 60}"
        )

        print(
            f"Testing: {exception_type}"
        )

        print(
            f"Transaction: "
            f"{package['transaction_id']}"
        )

        print(
            "=" * 60
        )

        try:

            result = investigate_exception(
                package
            )

            print(
                json.dumps(
                    result,
                    indent=2,
                    ensure_ascii=False
                )
            )

        except Exception as exc:

            print(
                f"ERROR: {exc}"
            )


if __name__ == "__main__":
    main()