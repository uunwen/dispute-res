import re

# Headings at level 2+ (## , ### , ...) are chunk boundaries. Level-1 titles and
# any preamble before the first heading are ignored.
_HEADING_RE = re.compile(r"^#{2,}\s+(.*)$")

# Extract a numeric section id like "2.3" or "7.1" from a heading. Falls back to
# the full heading text (e.g. "Appendix A: Glossary") when there is no number.
_SECTION_NUM_RE = re.compile(r"(?<!\d)(\d+(?:\.\d+)?)(?!\d)")


def _section_id(heading: str) -> str:
    m = _HEADING_RE.match(heading)
    body = m.group(1).strip() if m else heading.lstrip("#").strip()
    num = _SECTION_NUM_RE.search(body)
    return num.group(1) if num else body


def chunk_markdown(text: str) -> list[dict]:
    """Split a policy markdown document into sections on ``## `` and ``### `` headings.

    Returns a list of ``{"section": str, "text": str}`` dicts. Text before the
    first heading is ignored. Each chunk's ``section`` is its number (e.g. ``2.3``)
    so it can be cited.
    """
    chunks = []
    current_id = None
    current_lines: list[str] = []
    for line in text.splitlines():
        if _HEADING_RE.match(line):
            if current_id is not None:
                chunks.append({"section": current_id, "text": "\n".join(current_lines).strip()})
            current_id = _section_id(line)
            current_lines = [line.strip()]
        elif current_id is not None:
            current_lines.append(line.rstrip())
    if current_id is not None:
        chunks.append({"section": current_id, "text": "\n".join(current_lines).strip()})
    return chunks
