from __future__ import annotations

from enum import Enum


class CostTier(str, Enum):
    TINY = "tiny"
    PROBE = "probe"
    STUDY = "study"
    SPECIMEN = "specimen"
    EXTERNAL = "external"


class ApprovalRequired(PermissionError):
    def __init__(self, tier: CostTier) -> None:
        self.tier = tier
        super().__init__(f"explicit approval required for {tier.value} cost")


class CostGate:
    _GATED = frozenset({CostTier.STUDY, CostTier.SPECIMEN, CostTier.EXTERNAL})

    def require(self, tier: CostTier | str, *, approved: bool = False) -> None:
        try:
            normalized = CostTier(tier)
        except (TypeError, ValueError):
            raise ValueError(f"unknown cost tier: {tier}") from None
        if normalized in self._GATED and approved is not True:
            raise ApprovalRequired(normalized)
