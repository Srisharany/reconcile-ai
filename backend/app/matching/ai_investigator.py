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

Do NOT use Markdown.

You MUST return exactly these three sections:

LIKELY_CAUSE:
one short sentence

REASONING:
two or three short sentences

RECOMMENDED_ACTION:
one short sentence

Do not add any other headings.

Do not add any introduction.

Do not add any conclusion.

Do not use bullet points.
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

        "explanation":
            exception.get(
                "explanation"
            ),

        "recommended_action":
            exception.get(
                "recommended_action"
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
        default=str,
        indent=2
    )

    return f"""
Investigate this financial reconciliation exception.

Use ONLY the evidence provided below.

Do not invent missing facts.

If the evidence cannot prove the exact cause,
explicitly say:

The exact cause cannot be determined from the available evidence.

EVIDENCE:

{evidence_text}

Return exactly this format:

LIKELY_CAUSE:
one short sentence

REASONING:
two or three short sentences

RECOMMENDED_ACTION:
one short sentence
"""


# ============================================================
# TEXT CLEANING
# ============================================================

def clean_ai_text(text):

    if text is None:
        return ""

    text = str(text).strip()

    # Remove markdown code fences.
    text = text.replace(
        "```text",
        ""
    )

    text = text.replace(
        "```",
        ""
    )

    # Remove markdown emphasis.
    text = text.replace(
        "**",
        ""
    )

    text = text.replace(
        "__",
        ""
    )

    return text.strip()


# ============================================================
# TEXT PARSER
# ============================================================

def parse_response(text):

    text = clean_ai_text(text)

    result = {

        "likely_cause": "",

        "reasoning_summary": "",

        "recommended_action": "",
    }

    if not text:
        return result

    current_section = None

    sections = {

        "LIKELY_CAUSE:":
            "likely_cause",

        "LIKELY CAUSE:":
            "likely_cause",

        "REASONING:":
            "reasoning_summary",

        "REASONING SUMMARY:":
            "reasoning_summary",

        "RECOMMENDED_ACTION:":
            "recommended_action",

        "RECOMMENDED ACTION:":
            "recommended_action",
    }

    lines = text.splitlines()

    for line in lines:

        stripped = line.strip()

        if not stripped:
            continue

        upper_line = stripped.upper()

        matched_section = False

        for marker, field in sections.items():

            if upper_line.startswith(marker):

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
# RESPONSE VALIDATION
# ============================================================

def is_valid_ai_response(result):

    required_fields = [

        "likely_cause",

        "reasoning_summary",

        "recommended_action",
    ]

    for field in required_fields:

        value = result.get(
            field
        )

        if value is None:
            return False

        if not str(value).strip():
            return False

    return True


# ============================================================
# FALLBACK
# ============================================================

def deterministic_fallback(package):

    exception = package.get(
        "exception",
        {}
    )

    explanation = (
        exception.get(
            "explanation"
        )
        or
        exception.get(
            "reconciliation_reason"
        )
        or
        "The reconciliation exception requires investigation."
    )

    action = (
        exception.get(
            "recommended_action"
        )
        or
        "Manual investigation required."
    )

    exception_type = (
        exception.get(
            "exception_type"
        )
        or
        "UNKNOWN_EXCEPTION"
    )

    return {

        "likely_cause":
            f"The deterministic reconciliation engine identified a {exception_type} exception.",

        "reasoning_summary":
            explanation,

        "recommended_action":
            action,

        "ai_status":
            "FAILED",

        "ai_error":
            "Local AI investigation was unavailable or returned an invalid response.",
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

    # ========================================================
    # CONFIDENCE
    # ========================================================

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

    # ========================================================
    # FINANCIAL SAFETY
    # ========================================================

    # AI can NEVER authorize financial action.

    result[
        "should_auto_resolve"
    ] = False

    result[
        "requires_human_review"
    ] = True

    return result


# ============================================================
# AI INVESTIGATION
# ============================================================

def investigate_exception(package):

    prompt = build_prompt(
        package
    )

    last_error = None

    # ========================================================
    # ATTEMPT AI TWICE
    # ========================================================

    for attempt in range(2):

        try:

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
                        220,
                },
            )

            raw_output = (
                response
                .get(
                    "message",
                    {}
                )
                .get(
                    "content",
                    ""
                )
            )

            parsed = parse_response(
                raw_output
            )

            # =================================================
            # VALID RESPONSE
            # =================================================

            if is_valid_ai_response(
                parsed
            ):

                parsed[
                    "ai_status"
                ] = "SUCCESS"

                parsed[
                    "ai_error"
                ] = ""

                return apply_safety_gate(
                    parsed,
                    package
                )

            last_error = (
                "AI returned an incomplete "
                "structured response."
            )

        except Exception as exc:

            last_error = str(
                exc
            )

    # ========================================================
    # AI FAILED
    # ========================================================

    result = deterministic_fallback(
        package
    )

    result[
        "ai_status"
    ] = "FAILED"

    result[
        "ai_error"
    ] = (
        last_error
        or
        "AI investigation failed."
    )

    return apply_safety_gate(
        result,
        package
    )