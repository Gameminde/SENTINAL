"""Organ foundry exceptions."""
from __future__ import annotations


class ReceiptIntegrityError(Exception):
    """Raised when an organ receipt fails its integrity check (F-A3.9)."""
