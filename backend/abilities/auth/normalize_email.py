"""Email normalization ability atom."""


def normalize_email(email: str) -> str:
    return email.lower().strip()
