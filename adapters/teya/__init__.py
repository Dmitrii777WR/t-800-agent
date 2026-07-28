"""Teya Adapter — граница T-800 Factory → Teya onboarding (Phase 1+2)."""

from .profiles import (
    LEGACY_ALIASES,
    TEYA_PROFILES,
    is_teya_profile,
    match_brain_teya,
    normalize_profile,
)
from .discovery import resolve_teya_plugin_root
from .handoff import (
    ALLOWED_T800_STATUSES,
    FORBIDDEN_T800_STATUSES,
    apply_teya_verification,
    build_handoff,
    validate_handoff_for_t800_write,
)
from .evidence import ADAPTER_VERSION, ONBOARDING_GATE_VERSION, factory_provenance_metadata

__all__ = [
    "LEGACY_ALIASES",
    "TEYA_PROFILES",
    "is_teya_profile",
    "match_brain_teya",
    "normalize_profile",
    "resolve_teya_plugin_root",
    "ALLOWED_T800_STATUSES",
    "FORBIDDEN_T800_STATUSES",
    "apply_teya_verification",
    "build_handoff",
    "validate_handoff_for_t800_write",
    "ADAPTER_VERSION",
    "ONBOARDING_GATE_VERSION",
    "factory_provenance_metadata",
]
