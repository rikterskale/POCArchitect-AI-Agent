"""Harmless local behavior used to prove the verification boundary end to end."""


def trigger(value: str) -> str:
    """Return an observable result without network or host interaction."""
    return f"verified:{value}"
