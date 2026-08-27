import json
from pathlib import Path

from app.matching.ai_investigator import (
    investigate_exception,
)


BASE_DIR = Path(__file__).resolve().parents[2]

PROCESSED_DIR = (
    BASE_DIR / "data" / "processed"
)

EVIDENCE_FILE = (
    PROCESSED_DIR / "evidence_packages.json"
)

OUTPUT_FILE = (
    PROCESSED_DIR / "ai_investigations.json"
)


def main():

    print("=" * 60)
    print(
        "ReconcileAI — Pass 3: AI Investigation"
    )
    print("=" * 60)

    # --------------------------------------------------------
    # Load evidence
    # --------------------------------------------------------

    with open(
        EVIDENCE_FILE,
        "r",
        encoding="utf-8"
    ) as file:

        packages = json.load(file)

    print(
        f"\nEvidence packages: {len(packages)}"
    )

    results = []

    # --------------------------------------------------------
    # Investigate every exception
    # --------------------------------------------------------

    for index, package in enumerate(
        packages,
        start=1
    ):

        transaction_id = (
            package["transaction_id"]
        )

        exception_type = (
            package[
                "exception"
            ][
                "exception_type"
            ]
        )

        print(
            f"[{index}/{len(packages)}] "
            f"{transaction_id} "
            f"→ {exception_type}"
        )

        try:

            result = investigate_exception(
                package
            )

            results.append(
                result
            )

        except Exception as exc:

            print(
                f"  ERROR: {exc}"
            )

            results.append(
                {
                    "transaction_id":
                        transaction_id,

                    "exception_type":
                        exception_type,

                    "facts": [],

                    "observations": [],

                    "likely_cause":
                        "AI investigation failed.",

                    "confidence":
                        0.0,

                    "reasoning_summary":
                        str(exc),

                    "recommended_action":
                        "Manual investigation required.",

                    "should_auto_resolve":
                        False,

                    "requires_human_review":
                        True,
                }
            )

    # --------------------------------------------------------
    # Save
    # --------------------------------------------------------

    with open(
        OUTPUT_FILE,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            results,
            file,
            indent=2,
            ensure_ascii=False
        )

    # --------------------------------------------------------
    # Summary
    # --------------------------------------------------------

    print("\n")
    print("=" * 60)
    print(
        "PASS 3 — AI INVESTIGATION SUMMARY"
    )
    print("=" * 60)

    print(
        f"\nCompleted: "
        f"{len(results)}/{len(packages)}"
    )

    failed = sum(
        1
        for result in results
        if result["confidence"] == 0
    )

    human_review = sum(
        1
        for result in results
        if result[
            "requires_human_review"
        ]
    )

    auto_resolve = sum(
        1
        for result in results
        if result[
            "should_auto_resolve"
        ]
    )

    print(
        f"Failed investigations: "
        f"{failed}"
    )

    print(
        f"Human review required: "
        f"{human_review}"
    )

    print(
        f"Auto-resolution allowed: "
        f"{auto_resolve}"
    )

    if results:

        average_confidence = (
            sum(
                result["confidence"]
                for result in results
            )
            / len(results)
        )

        print(
            f"Average confidence: "
            f"{average_confidence:.2%}"
        )

    print(
        f"\nSaved to:"
        f"\n{OUTPUT_FILE}"
    )

    print(
        "\nPass 3 complete."
    )


if __name__ == "__main__":
    main()