"""Citation/reference system: a `bibliography:` file (deck.yaml) supplies numbered
references, cited from a slide body via `[@key]`/`[@key1; @key2]` or from an image via
its `reference`/`image_reference` field. Numbers are assigned deck-wide, in first-cited
order (`process_citations`, run once over the validated, pre-phase-expansion slide
list). On a `phase_in` slide, a citation's *footnote* only shows on the step(s) whose
bullet/image it belongs to (correlated via `phase_in.line_step_ranges`/`step_for_line`
against the citation's source line) — the final "everything undimmed" step shows the
union of every other step's citations. The inline `[1]` marker itself needs no such
handling: it's literal text inside its bullet's `<li>`, so it already dims/hides
exactly like the rest of that bullet via CSS. Numbering stays deck-global and
step-independent — only which steps *display* a given citation's footnote varies.

Two source formats, chosen by file extension (`load_bibliography`):

- `.bib`: a hand-rolled BibTeX parser (not the full spec — see `parse_bibtex`) formatted
  per the American Chemical Society (ACS) style, the only style implemented so far.
- anything else: a plain `"key": "citation text"` (optionally `: "doi"`) file, one entry
  per line, the citation text used verbatim as raw HTML ("pasted as-is").
"""

from __future__ import annotations

import html
import re
from dataclasses import dataclass, field, replace
from pathlib import Path

from . import phase_in
from .parser import SlideMakerError
from .schema import SlideConfig

_CITE_RE = re.compile(r"\[(@[^\]]+)\]")
_ENTRY_RE = re.compile(r"@(\w+)\s*\{\s*([^,\s]+)\s*,")
_FIELD_RE = re.compile(r"([A-Za-z][\w-]*)\s*=\s*")
_PLAIN_LINE_RE = re.compile(
    r'^"((?:[^"\\]|\\.)*)"\s*:\s*"((?:[^"\\]|\\.)*)"(?:\s*:\s*"((?:[^"\\]|\\.)*)")?$'
)


@dataclass
class ReferenceEntry:
    html: str
    doi_url: str | None = None


@dataclass
class CitationContext:
    key_to_number: dict[str, int] = field(default_factory=dict)
    by_number: dict[int, ReferenceEntry] = field(default_factory=dict)
    ordered: list[tuple[int, ReferenceEntry]] = field(default_factory=list)


def _normalize_doi(doi: str) -> str:
    doi = doi.strip()
    return doi if doi.lower().startswith("http") else f"https://doi.org/{doi}"


# --- BibTeX parsing (deliberately partial -- see the module docstring and CLAUDE.md
# for the documented subset this covers) -------------------------------------------


def _split_entries(text: str) -> list[tuple[str, str, str]]:
    """Every `@type{key, ...}` entry as (type, key, raw-field-text), tracking brace
    depth so a nested `{...}` inside a field value (e.g. `{DNA} nanotechnology`)
    doesn't prematurely end the entry."""
    entries = []
    for m in _ENTRY_RE.finditer(text):
        depth = 1
        i = m.end()
        while i < len(text) and depth > 0:
            if text[i] == "{":
                depth += 1
            elif text[i] == "}":
                depth -= 1
            i += 1
        entries.append((m.group(1).lower(), m.group(2).strip(), text[m.end() : i - 1]))
    return entries


def _parse_fields(body: str) -> dict[str, str]:
    fields: dict[str, str] = {}
    i, n = 0, len(body)
    while i < n:
        m = _FIELD_RE.match(body, i)
        if not m:
            i += 1
            continue
        name = m.group(1).lower()
        i = m.end()
        if i >= n:
            break
        if body[i] == "{":
            depth = 1
            j = i + 1
            while j < n and depth > 0:
                if body[j] == "{":
                    depth += 1
                elif body[j] == "}":
                    depth -= 1
                j += 1
            value, i = body[i + 1 : j - 1], j
        elif body[i] == '"':
            j = body.find('"', i + 1)
            j = j if j != -1 else n
            value, i = body[i + 1 : j], j + 1
        else:
            j = body.find(",", i)
            j = j if j != -1 else n
            value, i = body[i:j], j
        # inner {braces} are a BibTeX capitalization-protection convention with no
        # meaning once formatted (e.g. `{DNA} nanotechnology`) -- drop them, keeping
        # the text they wrap.
        value = value.replace("{", "").replace("}", "")
        fields[name] = re.sub(r"\s+", " ", value.strip())
    return fields


def _format_author(raw: str) -> str:
    raw = raw.strip()
    if "," in raw:
        last, _, rest = raw.partition(",")
        first_parts = rest.strip().split()
    else:
        parts = raw.split()
        if not parts:
            return ""
        last, first_parts = parts[-1], parts[:-1]
    initials = " ".join(f"{p[0].upper()}." for p in first_parts if p)
    last = last.strip()
    return f"{last}, {initials}" if initials else last


def _format_authors(raw: str) -> str:
    people = [p for p in re.split(r"\s+and\s+", raw, flags=re.IGNORECASE) if p.strip()]
    return "; ".join(_format_author(p) for p in people)


def _fmt_pages(raw: str) -> str:
    return re.sub(r"-{1,2}", "–", raw)


def format_acs(entry_type: str, fields: dict[str, str]) -> str:
    """Best-effort ACS-style citation text for one BibTeX entry. Missing optional
    fields are simply omitted rather than erroring; journal names are used exactly as
    given (no CASSI abbreviation lookup)."""
    esc = html.escape
    parts = []
    if fields.get("author"):
        parts.append(esc(_format_authors(fields["author"])))
    title = esc(fields.get("title", "")).rstrip(".")
    if title:
        parts.append(f"{title}.")
    year = esc(fields["year"]) if fields.get("year") else ""

    if entry_type == "article":
        segment = ""
        journal = fields.get("journal") or fields.get("journaltitle")
        if journal:
            segment += f"<i>{esc(journal)}</i>"
        if year:
            segment += f" <b>{year}</b>" if segment else f"<b>{year}</b>"
        if fields.get("volume"):
            segment += f", <i>{esc(fields['volume'])}</i>"
        if fields.get("pages"):
            segment += f", {esc(_fmt_pages(fields['pages']))}"
        if segment:
            parts.append(segment + ".")
    elif entry_type == "book":
        segment = ""
        if fields.get("publisher"):
            segment += esc(fields["publisher"])
            if fields.get("address"):
                segment += f": {esc(fields['address'])}"
        if year:
            segment += f", <b>{year}</b>" if segment else f"<b>{year}</b>"
        if segment:
            parts.append(segment + ".")
    elif entry_type in ("incollection", "inbook"):
        segment = ""
        if fields.get("booktitle"):
            segment += f"In <i>{esc(fields['booktitle'])}</i>"
        if fields.get("editor"):
            segment += f"; {esc(_format_authors(fields['editor']))}, Ed."
        if fields.get("publisher"):
            segment += f"; {esc(fields['publisher'])}"
            if fields.get("address"):
                segment += f": {esc(fields['address'])}"
        if year:
            segment += f", <b>{year}</b>" if segment else f"<b>{year}</b>"
        if fields.get("pages"):
            segment += f"; pp {esc(_fmt_pages(fields['pages']))}"
        if segment:
            parts.append(segment + ".")
    elif entry_type in ("inproceedings", "conference"):
        segment = ""
        if fields.get("booktitle"):
            segment += f"In <i>{esc(fields['booktitle'])}</i>"
        if year:
            segment += f", <b>{year}</b>" if segment else f"<b>{year}</b>"
        if fields.get("pages"):
            segment += f"; pp {esc(_fmt_pages(fields['pages']))}"
        if segment:
            parts.append(segment + ".")
    elif year:
        parts.append(f"<b>{year}</b>.")

    return " ".join(parts) if parts else "(untitled reference)"


def parse_bibtex(text: str) -> dict[str, ReferenceEntry]:
    result: dict[str, ReferenceEntry] = {}
    for entry_type, key, body in _split_entries(text):
        fields = _parse_fields(body)
        doi_url = _normalize_doi(fields["doi"]) if fields.get("doi") else None
        result[key] = ReferenceEntry(html=format_acs(entry_type, fields), doi_url=doi_url)
    return result


# --- Plain "key": "citation" [": "doi"]  format -------------------------------------


def _unescape(s: str) -> str:
    return s.replace('\\"', '"').replace("\\\\", "\\")


def parse_plain(text: str, source_name: str) -> dict[str, ReferenceEntry]:
    result: dict[str, ReferenceEntry] = {}
    for lineno, raw_line in enumerate(text.splitlines(), start=1):
        line = raw_line.strip()
        if not line:
            continue
        m = _PLAIN_LINE_RE.match(line)
        if not m:
            raise SlideMakerError(
                f"{source_name}:{lineno}: malformed reference line (expected "
                '\'"key": "citation text"\', optionally followed by \': "doi"\')'
            )
        key, citation, doi = m.groups()
        result[_unescape(key)] = ReferenceEntry(
            html=_unescape(citation), doi_url=_normalize_doi(_unescape(doi)) if doi else None
        )
    return result


def load_bibliography(path: Path) -> dict[str, ReferenceEntry]:
    if not path.is_file():
        raise SlideMakerError(f"bibliography file not found: {path}")
    text = path.read_text(encoding="utf-8")
    if path.suffix.lower() == ".bib":
        return parse_bibtex(text)
    return parse_plain(text, path.name)


# --- Numbering + in-body substitution -----------------------------------------------


def _parse_keys(raw: str) -> list[str]:
    return [k.strip().lstrip("@").strip() for k in raw.split(";") if k.strip()]


def find_citations(text: str) -> list[list[str]]:
    """Every `[@key]` / `[@key1; @key2]` span in `text`, as a list of key-lists in
    order of appearance."""
    return [_parse_keys(m.group(1)) for m in _CITE_RE.finditer(text)]


def process_citations(
    slide_configs: list[SlideConfig],
    bibliography: dict[str, ReferenceEntry] | None,
    strict: bool,  # noqa: ARG001 -- kept for signature symmetry with the rest of the pipeline
) -> tuple[list[SlideConfig], CitationContext]:
    """Assign deck-wide citation numbers in first-cited order, substitute `[@key]`
    spans in each slide's body with the final `<sup>` markup, and record each slide's
    deduplicated cited-number list for its footnote block. Must run on the validated,
    pre-phase-expansion slide list (see module docstring)."""
    ctx = CitationContext()

    def resolve(key: str, slide_index: int) -> int:
        if bibliography is None or key not in bibliography:
            raise SlideMakerError(f"unknown citation key '{key}' (no matching bibliography entry)", slide_index=slide_index)
        if key not in ctx.key_to_number:
            number = len(ctx.key_to_number) + 1
            entry = bibliography[key]
            ctx.key_to_number[key] = number
            ctx.by_number[number] = entry
            ctx.ordered.append((number, entry))
        return ctx.key_to_number[key]

    updated: list[SlideConfig] = []
    for slide in slide_configs:
        cited: list[int] = []
        by_step: dict[int, list[int]] = {}

        def note(number: int, step: int | None = None) -> None:
            if step is None:
                if number not in cited:
                    cited.append(number)
            else:
                bucket = by_step.setdefault(step, [])
                if number not in bucket:
                    bucket.append(number)

        # For a phase_in slide, a citation only belongs to the footnote of whichever
        # step's bullet it's textually inside of -- "only show the current highlighted
        # bullet/image's refs" (not the whole slide's accumulated set). Resolved via
        # each bullet's source line span (phase_in.line_step_ranges), correlated
        # against the citation's own line in the raw body.
        # Non-bullet layouts (split/image) have no per-bullet ranges, so any body
        # citation there falls through to "every step" below.
        ranges: list[tuple[int, int, int]] = []
        step_count = final_step = 0
        if slide.phase_in:
            step_count, final_step = phase_in.step_layout(slide)
            if slide.layout in phase_in.BULLET_LAYOUTS:
                ranges, _ = phase_in.line_step_ranges(slide.body, slide.phase_level)

        def substitute(match: re.Match, _slide=slide) -> str:
            numbers = [resolve(key, _slide.index) for key in _parse_keys(match.group(1))]
            if _slide.phase_in:
                line = _slide.body[: match.start()].count("\n")
                step = phase_in.step_for_line(ranges, line)
                steps = range(step_count) if step is None else (step,)
                for s in steps:
                    for n in numbers:
                        note(n, step=s)
            else:
                for n in numbers:
                    note(n)
            links = [
                f'<a href="{html.escape(ctx.by_number[n].doi_url)}" target="_blank" rel="noopener">{n}</a>'
                if ctx.by_number[n].doi_url
                else str(n)
                for n in numbers
            ]
            return f'<sup class="citation">[{",".join(links)}]</sup>'

        new_body = _CITE_RE.sub(substitute, slide.body) if slide.body else slide.body

        if slide.phase_in:
            # A phase_images[i] entry's reference belongs to every step that actually
            # displays that image -- the same clamp-to-last-entry rule expand_slide
            # uses to pick each step's image.
            n_images = len(slide.phase_images)
            for i, panel in enumerate(slide.phase_images):
                if not panel.reference:
                    continue
                number = resolve(panel.reference, slide.index)
                for s in range(step_count):
                    if min(s, n_images - 1) == i:
                        note(number, step=s)
            # A split panel's reference belongs to the step that reveals that panel.
            if slide.layout == "split":
                for i, panel in enumerate(slide.panels):
                    if panel.reference:
                        note(resolve(panel.reference, slide.index), step=i)
            # The final "everything undimmed" step (absent on the image layout, where
            # final_step == step_count) shows the union of every other step's
            # citations, matching every bullet/panel/image being back on screen too.
            if final_step < step_count:
                union: list[int] = []
                for s in range(final_step):
                    for n in by_step.get(s, []):
                        if n not in union:
                            union.append(n)
                by_step[final_step] = union
        else:
            if slide.image_reference:
                note(resolve(slide.image_reference, slide.index))
            for panel in (*slide.images, *slide.panels):
                if panel.reference:
                    note(resolve(panel.reference, slide.index))

        updated.append(replace(slide, body=new_body, citation_numbers=cited, citation_numbers_by_step=by_step))

    return updated, ctx
