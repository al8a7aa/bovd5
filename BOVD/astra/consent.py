"""
BÖVD · consent and feature-flag gate
============================================
Every feature calls :func:`require` BEFORE it stores anything. If the feature
flag is off, or the astronaut has not granted the consent category, a
:class:`ConsentError` is raised and nothing is written (tested in
tests/test_consent.py – "consent-off tests").

Standards alignment (designed in alignment with, not certified):
  ISO/IEC 29100 §5.2 consent and choice, §5.4 data minimisation;
  ISO/IEC 27701 §7.2.3–7.2.4 (obtaining/recording consent).
"""
from __future__ import annotations

from . import config
from .storage import Store


class ConsentError(PermissionError):
    """Feature disabled or consent missing – no data may be collected."""


def flag(feature: str) -> dict[str, object]:
    return dict(config.features()["flags"][feature])


def is_enabled(store: Store, feature: str) -> bool:
    override = store.get_setting(f"flag.{feature}")
    if override is not None:
        return bool(override)
    return bool(flag(feature)["enabled"])


def require(store: Store, feature: str, astronaut_id: str, category: str | None = None) -> None:
    """Raise ConsentError unless the feature is on and consent is granted."""
    if not is_enabled(store, feature):
        raise ConsentError(f"{feature} is disabled")
    cat = category or str(flag(feature)["consent_category"])
    if cat == "core_health":
        # core health readings are the purpose of the app; consent is given at
        # enrolment but can still be withdrawn explicitly.
        if store.consents(astronaut_id).get(cat) is False:
            raise ConsentError("core health consent withdrawn")
        return
    if not store.consents(astronaut_id).get(cat):
        raise ConsentError(f"consent '{cat}' not granted for {astronaut_id}")
