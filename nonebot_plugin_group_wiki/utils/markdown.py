from pathlib import Path


def title_from_markdown(text: str, fallback: str) -> str:
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("# "):
            return stripped.removeprefix("# ").strip() or fallback
    return fallback


def summary_from_markdown(text: str, max_chars: int = 180) -> str:
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or stripped.startswith(">"):
            continue
        return stripped[:max_chars]
    return text.strip().replace("\n", " ")[:max_chars]


def category_from_path(path: Path) -> str:
    return path.stem.strip()


def split_markdown_sections(text: str) -> list[str]:
    sections: list[str] = []
    current: list[str] = []
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("#") and not stripped.startswith("# "):
            if current:
                sections.append("\n".join(current).strip())
                current = []
        current.append(line)
    if current:
        sections.append("\n".join(current).strip())
    return [section for section in sections if section]
