import os
from typing import Iterable

def flatten(nested: Iterable[Iterable]) -> Iterable:
    """Flatten a nested iterable."""
    return (idx for sub in nested for idx in sub)
