from decimal import ROUND_HALF_UP, Decimal

from ..settings import get_settings

# Price per million tokens (USD)
_MODEL_RATES: dict[str, dict[str, Decimal]] = {
    "claude-sonnet-5": {
        "input": Decimal("2.00"),
        "output": Decimal("10.00"),
        "cache_read": Decimal("0.20"),
        "cache_write": Decimal("2.50"),
    },
    "claude-opus-5": {
        "input": Decimal("5.00"),
        "output": Decimal("25.00"),
        "cache_read": Decimal("0.50"),
        "cache_write": Decimal("6.25"),
    },
}

_ONE_MILLION = Decimal("1000000")


def compute_cost_usd(
    model: str,
    *,
    input_tokens: int,
    output_tokens: int,
    cache_read_tokens: int = 0,
    cache_write_tokens: int = 0,
) -> Decimal:
    """Compute the exact USD cost for an LLM call based on model rates and token counts."""
    rates = _MODEL_RATES.get(model)
    if rates is None:
        # Fall back to Sonnet 5 rates if unknown variant
        rates = _MODEL_RATES["claude-sonnet-5"]

    cost = (
        (Decimal(input_tokens) * rates["input"])
        + (Decimal(output_tokens) * rates["output"])
        + (Decimal(cache_read_tokens) * rates["cache_read"])
        + (Decimal(cache_write_tokens) * rates["cache_write"])
    ) / _ONE_MILLION

    settings = get_settings()
    if settings.llm_inference_geo == "us":
        cost *= Decimal("1.1")

    # Round to 4 decimal places for Numeric(8, 4) schema column
    return cost.quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)
