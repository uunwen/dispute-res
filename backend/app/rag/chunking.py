import re


def _section_id(heading: str) -> str:
    body = heading[3:].strip() if heading.startswith("## ") else heading.strip()
    m = re.match(r"^(\d+(?:\.\d+)?)", body)
    return m.group(1) if m else body


def chunk_markdown(text: str) -> list[dict]:
    """Split a policy markdown document into sections on ``## `` headings.

    Returns a list of ``{"section": str, "text": str}`` dicts. Text before the
    first level-2 heading is ignored.
    """
    chunks = []
    current_id = None
    current_lines: list[str] = []
    for line in text.splitlines():
        if line.startswith("## "):
            if current_id is not None:
                chunks.append({"section": current_id, "text": "\n".join(current_lines).strip()})
            current_id = _section_id(line)
            current_lines = [line.strip()]
        elif current_id is not None:
            current_lines.append(line.rstrip())
    if current_id is not None:
        chunks.append({"section": current_id, "text": "\n".join(current_lines).strip()})
    return chunks
