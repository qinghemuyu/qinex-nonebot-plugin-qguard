def extract_traceback(text: str) -> str | None:
    marker = "Traceback (most recent call last):"
    index = text.rfind(marker)
    if index < 0:
        return None
    return text[index:]
