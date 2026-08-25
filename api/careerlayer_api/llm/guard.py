from datetime import date, datetime

from ..settings import get_settings


class PrivacyGateError(Exception):
    """Raised when an LLM call is blocked by the privacy and data processing gate."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


def check_privacy_gate(is_fixture: bool = False) -> None:
    """Enforce the Phase 3 privacy launch gate (Section 12.2).

    Rules:
    1. 'disabled': The default. No provider call is made, ever.
    2. 'fixtures_only': Only documents explicitly marked is_fixture=True may be processed.
    3. 'production': Requires LLM_PRIVACY_ATTESTATION_ID to be set, and LLM_PRIVACY_VERIFIED_AT
       to be a valid ISO date less than 365 days old. Otherwise fails closed.
    """
    settings = get_settings()
    mode = (settings.llm_data_processing_mode or "disabled").strip().lower()

    if mode == "disabled":
        raise PrivacyGateError(
            "llm_disabled",
            "LLM data processing is currently disabled.",
        )

    if mode == "fixtures_only":
        if not is_fixture:
            raise PrivacyGateError(
                "privacy_gate",
                "Real user documents cannot be sent to LLM providers in fixtures_only mode.",
            )
        return

    if mode == "production":
        attestation_id = settings.llm_privacy_attestation_id
        if not attestation_id or not attestation_id.strip():
            raise PrivacyGateError(
                "privacy_gate",
                "Production LLM calls require a verified LLM_PRIVACY_ATTESTATION_ID.",
            )

        verified_at_str = settings.llm_privacy_verified_at
        if not verified_at_str or not verified_at_str.strip():
            raise PrivacyGateError(
                "privacy_gate",
                "Production LLM calls require LLM_PRIVACY_VERIFIED_AT date.",
            )

        try:
            verified_date = datetime.strptime(verified_at_str.strip(), "%Y-%m-%d").date()
        except ValueError as exc:
            raise PrivacyGateError(
                "privacy_gate",
                "LLM_PRIVACY_VERIFIED_AT must be a valid date in YYYY-MM-DD format.",
            ) from exc

        today = date.today()
        age_days = (today - verified_date).days
        if age_days < 0 or age_days > 365:
            raise PrivacyGateError(
                "privacy_gate",
                f"Production privacy attestation expired ({age_days} days old, max 365).",
            )
        return

    raise PrivacyGateError(
        "privacy_gate",
        f"Unknown LLM data processing mode: {mode}",
    )
