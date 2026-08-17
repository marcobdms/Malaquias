"""Overlays de revisión humana sin modificar el gold original."""

from .overlay import apply_overlay, evaluate_label_views, validate_overlay

__all__ = ["apply_overlay", "evaluate_label_views", "validate_overlay"]
