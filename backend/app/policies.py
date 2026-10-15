"""Read-only access to the policy documents.

Parses ``backend/policies/*.md`` into structured sections for the
``GET /meta/policies`` endpoint. Each markdown file uses ``###`` headings for
its sections; ``precedent.md`` sections are additionally tagged ``precedent``.
"""

import re
from pathlib import Path

from app.schemas.api import PolicySection

POLICIES_DIR = Path(__file__).resolve().parents[1] / "policies"

_SECTION_RE = re.compile(r"^###\s+(?:Precedent\s+)?(\d+(?:\.\d+)*)[:.\s]*(.*)$")


def _parse_file(path: Path) -> list[PolicySection]:
    tag = "precedent" if path.name == "precedent.md" else None
    sections: list[PolicySection] = []
    current_id: str | None = None
    current_title: str = ""
    body: list[str] = []

    def flush() -> None:
        if current_id is None:
            return
        sections.append(
            PolicySection(
                id=current_id,
                title=current_title.strip(),
                text="\n".join(body).strip(),
                source=path.name,
                tag=tag,
            )
        )

    for line in path.read_text(encoding="utf-8").splitlines():
        match = _SECTION_RE.match(line)
        if match:
            flush()
            current_id = match.group(1)
            current_title = match.group(2)
            body = []
        elif current_id is not None and line.strip() != "---":
            body.append(line)
    flush()
    return sections


def load_policy_sections() -> list[PolicySection]:
    """Return every policy section across all markdown files, ordered by file."""
    sections: list[PolicySection] = []
    for path in sorted(POLICIES_DIR.glob("*.md")):
        sections.extend(_parse_file(path))
    return sections
