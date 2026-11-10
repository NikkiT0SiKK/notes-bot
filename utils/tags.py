import re

TAG_RE = re.compile(r"#(\w+)", re.UNICODE)


def extract_tags(text: str) -> tuple[str, list[str]]:
    """Возвращает (текст_без_тегов, список_уникальных_тегов)."""
    tags = [t.lower() for t in TAG_RE.findall(text)]
    # убираем дубликаты с сохранением порядка
    seen = set()
    unique = []
    for t in tags:
        if t not in seen:
            seen.add(t)
            unique.append(t)

    clean_text = TAG_RE.sub("", text).strip()
    clean_text = re.sub(r"\s+", " ", clean_text)
    return clean_text, unique