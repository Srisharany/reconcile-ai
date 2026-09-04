def get_risk_amount(record):
    """
    Return the actual financial risk.

    Priority:
    1. amount_at_risk if it is a valid non-zero value
    2. amount_difference
    3. 0
    """

    try:
        amount_at_risk = float(
            record.get("amount_at_risk") or 0
        )
    except (
        TypeError,
        ValueError,
    ):
        amount_at_risk = 0.0

    if amount_at_risk != 0:
        return abs(amount_at_risk)

    try:
        amount_difference = float(
            record.get("amount_difference") or 0
        )
    except (
        TypeError,
        ValueError,
    ):
        amount_difference = 0.0

    return abs(amount_difference)