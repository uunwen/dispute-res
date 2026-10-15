import { useEffect, useMemo, useState } from "react";
import { api, type PolicySection } from "../api";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

/* ============================================================
 * Policies — read from GET /meta/policies. Sections are grouped
 * by source file and can be searched / filtered. Precedent
 * rulings carry a "precedent" tag.
 * ============================================================ */

const SOURCE_LABEL: Record<string, string> = {
  "general_principles.md": "General principles",
  "no_show_fee.md": "No-show",
  "route_deviation.md": "Route deviation",
  "fare_surge_promo.md": "Fare & surge",
  "property_damage.md": "Property damage",
  "safety_incident.md": "Safety",
  "precedent.md": "Precedents",
};

const SOURCE_ORDER = [
  "general_principles.md",
  "route_deviation.md",
  "no_show_fee.md",
  "fare_surge_promo.md",
  "property_damage.md",
  "safety_incident.md",
  "precedent.md",
];

/* Maps a source file to the colour tint used by the id chip. */
const SOURCE_PART: Record<string, string> = {
  "general_principles.md": "general",
  "no_show_fee.md": "no_show",
  "route_deviation.md": "route_deviation",
  "fare_surge_promo.md": "route_deviation",
  "property_damage.md": "property_damage",
  "safety_incident.md": "safety",
  "precedent.md": "general",
};

function sourceLabel(source: string): string {
  return SOURCE_LABEL[source] ?? source.replace(/\.md$/, "").replace(/_/g, " ");
}

function sourcePart(source: string): string {
  return SOURCE_PART[source] ?? "general";
}

function sourceOrder(source: string): number {
  const idx = SOURCE_ORDER.indexOf(source);
  return idx === -1 ? SOURCE_ORDER.length : idx;
}

const COLLAPSED_CHAR_BUDGET = 240;

function SectionCard({ section }: { section: PolicySection }) {
  const [open, setOpen] = useState(false);
  const isLong = section.text.length > COLLAPSED_CHAR_BUDGET;
  const visible =
    open || !isLong
      ? section.text
      : `${section.text.slice(0, COLLAPSED_CHAR_BUDGET).trimEnd()}…`;

  return (
    <article className="rp-policy-card" data-part={sourcePart(section.source)}>
      <header className="rp-policy-card__head">
        <code className="rp-policy-card__id">{section.id}</code>
        <h3 className="rp-policy-card__title">{section.title}</h3>
        {section.tag === "precedent" && (
          <span className="rp-policy-card__tag">precedent</span>
        )}
      </header>
      <p className="rp-policy-card__source">{section.source}</p>
      <div className="rp-policy-card__body" style={{ whiteSpace: "pre-wrap" }}>
        <ReactMarkdown remarkPlugins={[remarkGfm]}>{visible}</ReactMarkdown>
      </div>
      {isLong && (
        <button
          type="button"
          className="rp-policy-card__toggle"
          onClick={() => setOpen((v) => !v)}
          aria-expanded={open}
        >
          {open ? "Show less" : "Show more"}
        </button>
      )}
    </article>
  );
}

export default function Policies() {
  const [sections, setSections] = useState<PolicySection[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [source, setSource] = useState<string>("all");
  const [query, setQuery] = useState("");

  useEffect(() => {
    let cancelled = false;
    api
      .getPolicies()
      .then((s) => {
        if (!cancelled) setSections(s);
      })
      .catch((e) => {
        if (!cancelled)
          setError(e instanceof Error ? e.message : "Failed to load policies.");
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const sources = useMemo(() => {
    if (!sections) return [];
    const seen = new Set<string>();
    for (const s of sections) seen.add(s.source);
    return [...seen].sort((a, b) => sourceOrder(a) - sourceOrder(b));
  }, [sections]);

  const groups = useMemo(() => {
    if (!sections) return [];
    const q = query.trim().toLowerCase();
    return sources
      .filter((src) => source === "all" || src === source)
      .map((src) => {
        const rules = sections.filter(
          (s) =>
            s.source === src &&
            (q === "" ||
              s.id.toLowerCase().includes(q) ||
              s.title.toLowerCase().includes(q) ||
              s.text.toLowerCase().includes(q)),
        );
        return { source: src, rules };
      })
      .filter((g) => g.rules.length > 0);
  }, [sections, sources, source, query]);

  const totalShown = groups.reduce((acc, g) => acc + g.rules.length, 0);
  const totalSections = sections?.length ?? 0;

  return (
    <div className="rp-page rp-policies">
      <div className="rp-page-header">
        <div>
          <h1>Dispute Policy</h1>
          <p>
            Policy sections sourced from <code>backend/policies/*.md</code>.
            Precedent rulings are tagged <em>precedent</em>.
          </p>
        </div>
      </div>

      <div className="rp-card rp-policies__toolbar">
        <div
          className="rp-tabs"
          role="tablist"
          aria-label="Policy source filter"
        >
          <button
            type="button"
            role="tab"
            aria-selected={source === "all"}
            className={source === "all" ? "active" : ""}
            onClick={() => setSource("all")}
          >
            All
          </button>
          {sources.map((s) => (
            <button
              key={s}
              type="button"
              role="tab"
              aria-selected={source === s}
              className={source === s ? "active" : ""}
              onClick={() => setSource(s)}
            >
              {sourceLabel(s)}
            </button>
          ))}
        </div>
        <div className="rp-field rp-policies__search">
          <span>Search</span>
          <input
            type="search"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Section id, title or text…"
            aria-label="Search sections"
          />
        </div>
        <span className="rp-policies__count">
          {totalShown} of {totalSections} sections
        </span>
      </div>

      {error ? (
        <div className="rp-recent__state rp-recent__state--error">
          <strong>Couldn't load policies.</strong>
          <p>{error}</p>
        </div>
      ) : sections === null ? (
        <div className="rp-recent__state">Loading policies…</div>
      ) : groups.length === 0 ? (
        <div className="rp-card rp-card--padded">
          <h3 style={{ marginTop: 0 }}>No matching sections.</h3>
          <p className="rp-muted">
            Try a different search term or source filter.
          </p>
        </div>
      ) : (
        groups.map((g) => (
          <section className="rp-policies__group" key={g.source}>
            <header className="rp-policies__group-head">
              <h2>{sourceLabel(g.source)}</h2>
              <p className="rp-muted rp-small">{g.source}</p>
            </header>
            <div className="rp-policies__grid">
              {g.rules.map((r) => (
                <SectionCard key={`${r.source}-${r.id}`} section={r} />
              ))}
            </div>
          </section>
        ))
      )}
    </div>
  );
}
