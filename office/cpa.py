"""Calculate first-order acquisition thresholds without a model or paid integration."""

from decimal import Decimal
import re


def calculate_cpa(payload):
    if not isinstance(payload, dict):
        raise ValueError("Provide your first-order revenue and costs.")
    currency = payload.get("currency")
    if not isinstance(currency, str) or not re.fullmatch(r"[A-Za-z]{3}", currency.strip()):
        raise ValueError("Enter a three-letter currency code, such as USD.")

    def amount(key, label, default=None):
        value = payload.get(key, default)
        if not isinstance(value, str) or not re.fullmatch(r"[0-9]{1,9}(?:\.[0-9]{1,2})?", value.strip()):
            raise ValueError(f"Enter {label} as an amount with up to two decimal places.")
        return Decimal(value)

    revenue = amount("revenue", "first-order revenue")
    if revenue <= 0:
        raise ValueError("First-order revenue must be greater than zero.")
    costs = (
        amount("product_cost", "product cost")
        + amount("fulfillment", "fulfillment and shipping cost")
        + amount("other_costs", "other variable costs")
    )
    reserve = amount("profit_target", "the contribution target", "0")
    contribution = revenue - costs
    available = contribution - reserve
    return {
        "currency": currency.strip().upper(),
        "variable_costs": f"{costs:.2f}",
        "pre_ad_contribution": f"{contribution:.2f}",
        "profit_target": f"{reserve:.2f}",
        "break_even_cpa": f"{contribution:.2f}" if contribution >= 0 else None,
        "target_cpa": f"{available:.2f}" if available >= 0 else None,
        "break_even_roas": f"{revenue / contribution:.2f}" if contribution > 0 else None,
    }
