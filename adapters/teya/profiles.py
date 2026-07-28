"""Profile matcher for Teya adapter + brain-teya activation."""

from __future__ import annotations

from typing import Any

TEYA_PROFILES = frozenset(
    {
        "teya-plugin-dev",
        "teya-client",
        "teya-pro",  # legacy alias (normalized below)
    }
)

LEGACY_ALIASES = {
    "teya-pro": ("teya-plugin-dev", "teya-client"),
}

# Profiles that activate adapter + brain-teya (including legacy)
BRAIN_TEYA_TRIGGERS = frozenset(
    {
        "teya-plugin-dev",
        "teya-client",
        "teya-pro",
    }
)


def normalize_profile(profile: str | None) -> str:
    """Return canonical profile id (legacy teya-pro stays as alias id for matching)."""
    return str(profile or "").strip().lower()


def is_teya_profile(profile: str | None) -> bool:
    """True if profile activates Teya adapter (including legacy alias)."""
    p = normalize_profile(profile)
    if p in {"teya-plugin-dev", "teya-client", "teya-pro"}:
        return True
    if p.startswith("teya-") and p in TEYA_PROFILES:
        return True
    return False


def match_brain_teya(profile: str | None, *, target_plugin: str | None = None) -> dict[str, Any]:
    """Machine-checkable brain-teya activation decision.

    Activates for: teya-plugin-dev, teya-client, legacy teya-pro
    (also when target_plugin carries those ids).
    """
    candidates = [
        normalize_profile(profile),
        normalize_profile(target_plugin),
    ]
    matched = None
    for c in candidates:
        if c in BRAIN_TEYA_TRIGGERS:
            matched = c
            break

    legacy = matched == "teya-pro"
    return {
        "activate": matched is not None,
        "matched_profile": matched,
        "legacy_alias": legacy,
        "canonical_profiles": list(LEGACY_ALIASES["teya-pro"]) if legacy else (
            [matched] if matched else []
        ),
        "adapter_required": matched is not None,
        "brain": "t-800-brain-teya" if matched else None,
    }


def adapter_applies(profile: str | None) -> bool:
    """Integrator must call Teya adapter only when True."""
    return is_teya_profile(profile)
