"""
Phase 2: Layout-aware PDF extraction via docling.

Returns a list of block dicts that downstream chunkers consume:
  {"page": int, "text": str, "is_heading": bool}

ColPali fallback is wired as a placeholder: pages with no extractable text
log a warning; full ColPali inference is added in Phase 6.
"""
from __future__ import annotations

import logging
from pathlib import Path

logger = logging.getLogger(__name__)

# Block type labels from docling item class names
_HEADING_TYPES = {"SectionHeaderItem", "TitleItem"}


def _needs_vlm_fallback(page_text: str) -> bool:
    return not page_text.strip()


def _extract_with_colpali(page_number: int) -> list[dict]:
    """Phase 6 placeholder — full ColPali inference replaces this."""
    logger.warning("Page %d: no text extracted by docling; ColPali fallback not yet active.", page_number)
    return []


def extract(pdf_path: str) -> list[dict]:
    """
    Parse a PDF with docling and return structured blocks.

    Each block: {"page": int, "text": str, "is_heading": bool}
    Repeated header/footer text (appearing on >70% of pages) is stripped.
    """
    try:
        from docling.document_converter import DocumentConverter
    except ImportError:
        logger.error("docling not installed — run: uv sync")
        raise

    converter = DocumentConverter()
    result = converter.convert(pdf_path)
    doc = result.document

    raw_blocks: list[dict] = []

    try:
        # Docling 2.x API: iterate_items() yields (item, level) tuples
        for item, _level in doc.iterate_items():
            item_type = type(item).__name__
            text = getattr(item, "text", "") or ""
            text = text.strip()
            if not text:
                continue

            # Extract page number from provenance
            page_no = 1
            if hasattr(item, "prov") and item.prov:
                prov = item.prov[0] if isinstance(item.prov, (list, tuple)) else item.prov
                page_no = getattr(prov, "page_no", 1) or 1

            raw_blocks.append({
                "page": page_no,
                "text": text,
                "is_heading": item_type in _HEADING_TYPES,
            })
    except AttributeError:
        # Fallback: export to markdown and treat every line as a paragraph
        logger.warning("docling iterate_items() not available; falling back to markdown export")
        md = doc.export_to_markdown()
        for i, line in enumerate(md.splitlines()):
            line = line.strip()
            if not line:
                continue
            is_heading = line.startswith("#")
            raw_blocks.append({"page": 1, "text": line.lstrip("#").strip(), "is_heading": is_heading})

    if not raw_blocks:
        logger.warning("No blocks extracted from %s", pdf_path)

    # ── noise filter: remove text appearing on >70% of unique pages ──────────
    raw_blocks = _remove_repeated_noise(raw_blocks)

    # ── ColPali fallback for empty pages ──────────────────────────────────────
    pages_with_text = {b["page"] for b in raw_blocks}
    all_pages = set(range(1, max((b["page"] for b in raw_blocks), default=1) + 1))
    for empty_page in all_pages - pages_with_text:
        raw_blocks.extend(_extract_with_colpali(empty_page))

    raw_blocks.sort(key=lambda b: (b["page"],))
    return raw_blocks


def _remove_repeated_noise(blocks: list[dict]) -> list[dict]:
    page_count = max((b["page"] for b in blocks), default=1)

    # Need at least 3 pages to reliably detect repeated headers/footers.
    # On 1–2 page documents, every line appears on most pages by definition.
    if page_count < 3:
        return blocks

    threshold = 0.7 * page_count  # strings on >70% of pages = noise

    text_page_sets: dict[str, set[int]] = {}
    for b in blocks:
        text_page_sets.setdefault(b["text"], set()).add(b["page"])

    noise = {text for text, pages in text_page_sets.items() if len(pages) >= threshold}
    if noise:
        logger.info("Removing %d noise strings (repeated headers/footers)", len(noise))

    return [b for b in blocks if b["text"] not in noise]
