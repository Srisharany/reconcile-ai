import json
from pathlib import Path

import ollama


# ============================================================
# PATHS
# ============================================================

BASE_DIR = Path(__file__).resolve().parents[2]

PROCESSED_DATA_DIR = (
    BASE_DIR / "data" / "processed"
)


# ============================================================
# LOCAL MODEL
# ============================================================

MODEL = "llama3.2:3b"


# ============================================================
# SYSTEM PROMPT
# ============================================================

SYSTEM_PROMPT = """
You are a financial reconciliation investigation assistant.

Use ONLY the supplied evidence.

Do not invent facts.

Do not invent:
- amounts
- dates
- transaction IDs
- merchants
- fees
- refunds
- settlements

A possible cause is not a confirmed cause.

Be concise.

Return plain text only.

Use exactly these three sections:

LIKELY_CAUSE:
one short sentence

REASONING:
two or three short sentences

RECOMMENDED_ACTION:
one short sentence
"""


# ============================================================
# COMPACT EVIDENCE
# ============================================================

def build_compact_evidence(package):

    exception = package.get(
        "exception",
        {}
    )

    gateway = package.get(
        "gateway",
        {}
    )

    order = package.get(
        "order",
        {}
    )

    bank = package.get(
        "bank",
        {}
    )

    matching = package.get(
        "matching"
    )

    evidence = {

        "transaction_id":
            package.get(
                "transaction_id"
            ),

        "exception_type":
            exception.get(
                "exception_type"
            ),

        "severity":
            exception.get(
                "severity"
            ),

        "amount_at_risk":
            exception.get(
                "amount_at_risk"
            ),

        "amount_difference":
            exception.get(
                "amount_difference"
            ),

        "gateway": {

            "transaction_id":
                gateway.get(
                    "transaction_id"
                ),

            "order_reference":
                gateway.get(
                    "order_reference"
                ),

            "merchant":
                gateway.get(
                    "merchant"
                ),

            "amount":
                gateway.get(
                    "amount"
                ),

            "currency":
                gateway.get(
                    "currency"
                ),

            "transaction_date":
                gateway.get(
                    "transaction_date"
                ),
        },

        "order": {

            "order_id":
                order.get(
                    "order_id"
                ),

            "merchant":
                order.get(
                    "merchant"
                ),

            "amount":
                order.get(
                    "amount"
                ),
        },

        "bank": {

            "bank_reference":
                bank.get(
                    "bank_reference"
                ),

            "transaction_reference":
                bank.get(
                    "transaction_reference"
                ),

            "merchant":
                bank.get(
                    "merchant"
                ),

            "settlement_amount":
                bank.get(
                    "settlement_amount"
                ),

            "currency":
                bank.get(
                    "currency"
                ),

            "settlement_date":
                bank.get(
                    "settlement_date"
                ),
        },
    }

    if matching is not None:

        evidence["matching"] = matching

    return evidence


# ============================================================
# PROMPT
# ============================================================

def build_prompt(package):

    evidence = build_compact_evidence(
        package
    )

    evidence_text = json.dumps(
        evidence,
        ensure_ascii=False,
        default=str
    )

    return f"""
Investigate this financial reconciliation exception.

EVIDENCE:

{evidence_text}

Remember:

Use ONLY these facts.

Do not invent missing information.

If the cause cannot be proven,
say "The exact cause cannot be determined
from the available evidence."

Return exactly:

LIKELY_CAUSE:
...

REASONING:
...

RECOMMENDED_ACTION:
...
"""


# ============================================================
# TEXT PARSER
# ============================================================

def parse_response(text):

    text = text.strip()

    result = {
        "likely_cause": "",
        "reasoning_summary": "",
        "recommended_action": "",
    }

    current_section = None

    sections = {
        "LIKELY_CAUSE:":
            "likely_cause",

        "REASONING:":
            "reasoning_summary",

        "RECOMMENDED_ACTION:":
            "recommended_action",
    }

    lines = text.splitlines()

    for line in lines:

        stripped = line.strip()

        if not stripped:
            continue

        matched_section = False

        for marker, field in sections.items():

            if stripped.upper().startswith(
                marker
            ):

                current_section = field

                content = stripped[
                    len(marker):
                ].strip()

                if content:

                    result[field] = content

                matched_section = True

                break

        if matched_section:
            continue

        if current_section:

            if result[current_section]:

                result[current_section] += (
                    " " + stripped
                )

            else:

                result[current_section] = (
                    stripped
                )

    return result


# ============================================================
# FALLBACK
# ============================================================

def deterministic_fallback(package):

    exception = package.get(
        "exception",
        {}
    )

    exception_type = (
        exception.get(
            "exception_type"
        )
    )

    explanation = (
        exception.get(
            "explanation",
            "The reconciliation exception requires investigation."
        )
    )

    action = (
        exception.get(
            "recommended_action",
            "Manual investigation required."
        )
    )

    return {

        "likely_cause":
            explanation,

        "reasoning_summary":
            (
                "The deterministic reconciliation "
                "engine identified this exception. "
                "The local AI explanation was not "
                "available, so no additional cause "
                "is inferred."
            ),

        "recommended_action":
            action,

        "ai_status":
            "FALLBACK",

        "ai_error":
            "Local AI response could not be parsed.",
    }


# ============================================================
# SAFETY GATE
# ============================================================

def apply_safety_gate(
    result,
    package
):

    exception = package.get(
        "exception",
        {}
    )

    result[
        "transaction_id"
    ] = package.get(
        "transaction_id"
    )

    result[
        "exception_type"
    ] = exception.get(
        "exception_type"
    )

    # Confidence remains deterministic.
    try:

        confidence = float(
            exception.get(
                "confidence",
                0.0
            )
        )

    except (
        TypeError,
        ValueError
    ):

        confidence = 0.0

    confidence = max(
        0.0,
        min(
            1.0,
            confidence
        )
    )

    result[
        "confidence"
    ] = round(
        confidence,
        4
    )

    # NEVER allow AI to authorize financial action.

    result[
        "should_auto_resolve"
    ] = False

    result[
        "requires_human_review"
    ] = True

    return result


# ============================================================
# INVESTIGATE
# ============================================================

def investigate_exception(
    package
):

    try:

        prompt = build_prompt(
            package
        )

        response = ollama.chat(

            model=MODEL,

            messages=[

                {
                    "role":
                        "system",

                    "content":
                        SYSTEM_PROMPT,
                },

                {
                    "role":
                        "user",

                    "content":
                        prompt,
                },
            ],

            options={

                "temperature":
                    0,

                "num_predict":
                    180,
            },
        )

        raw_output = (
            response[
                "message"
            ][
                "content"
            ]
        )

        parsed = parse_response(
            raw_output
        )

        # If the model produced nothing useful,
        # use deterministic fallback.

        if not parsed[
            "likely_cause"
        ]:

            return apply_safety_gate(
                deterministic_fallback(
                    package
                ),
                package
            )

        parsed[
            "ai_status"
        ] = "SUCCESS"

        parsed = apply_safety_gate(
            parsed,
            package
        )

        return parsed

    except Exception as exc:

        result = deterministic_fallback(
            package
        )

        result[
            "ai_error"
        ] = str(exc)

        return apply_safety_gate(
            result,
            package
        )