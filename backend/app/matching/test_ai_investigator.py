import json

from app.matching.ai_investigator import (
    investigate_exception,
)


EVIDENCE_FILE = (
    "data/processed/evidence_packages.json"
)


def main():

    # --------------------------------------------------------
    # Load evidence packages
    # --------------------------------------------------------

    with open(
        EVIDENCE_FILE,
        "r",
        encoding="utf-8"
    ) as file:

        packages = json.load(file)

    if not packages:

        raise RuntimeError(
            "No evidence packages found."
        )

    # --------------------------------------------------------
    # Test ONE exception only
    # --------------------------------------------------------

    package = packages[0]

    print("=" * 60)

    print(
        "ReconcileAI — Local AI Investigator Test"
    )

    print("=" * 60)

    print(
        f"\nTesting transaction: "
        f"{package['transaction_id']}"
    )

    print(
        f"Exception: "
        f"{package['exception']['exception_type']}"
    )

    # --------------------------------------------------------
    # Run local AI investigator
    # --------------------------------------------------------

    result = investigate_exception(
        package
    )

    # --------------------------------------------------------
    # Display result
    # --------------------------------------------------------

    print("\nAI RESULT")
    print("=" * 60)

    print(
        json.dumps(
            result,
            indent=2,
            ensure_ascii=False
        )
    )

    print(
        "\nLocal AI test complete."
    )


if __name__ == "__main__":
    main()