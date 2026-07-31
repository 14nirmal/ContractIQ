"""
ContractIQ — Parser Agent

Cleans, normalizes, and sections raw contract text extracted by the OCR pipeline.
"""

import logging
import re
from typing import Any

logger = logging.getLogger(__name__)


def clean_text(raw_text: str) -> str:
    """
    Clean and normalize raw extracted text.

    - Collapse excessive whitespace
    - Remove non-printable characters
    - Normalize line breaks
    - Strip leading/trailing whitespace per line
    """
    if not raw_text:
        return ""

    # Remove non-printable chars (keep newlines and tabs)
    text = re.sub(r'[^\x20-\x7E\n\t]', ' ', raw_text)

    # Normalize line breaks
    text = text.replace('\r\n', '\n').replace('\r', '\n')

    # Collapse multiple blank lines into double newline
    text = re.sub(r'\n{3,}', '\n\n', text)

    # Collapse multiple spaces into single space (per line)
    lines = []
    for line in text.split('\n'):
        cleaned = re.sub(r' {2,}', ' ', line.strip())
        lines.append(cleaned)

    text = '\n'.join(lines)

    return text.strip()


def split_into_sections(text: str) -> list[dict[str, Any]]:
    """
    Split contract text into logical sections based on common heading patterns.

    Returns:
        List of dicts with keys: title, content, section_index
    """
    if not text:
        return []

    # Common contract section heading patterns
    heading_patterns = [
        r'^(?:ARTICLE|SECTION|CLAUSE)\s+[\dIVXivx]+[.:]?\s+.*$',
        r'^\d+[.)]\s+[A-Z][A-Za-z\s]+$',
        r'^[A-Z][A-Z\s]{4,}$',  # ALL CAPS headings
        r'^\d+\.\d*\s+[A-Z].*$',  # Numbered sections like "1.1 Definitions"
    ]
    combined_pattern = '|'.join(f'({p})' for p in heading_patterns)

    sections = []
    current_title = "Preamble"
    current_content_lines = []
    section_index = 0

    for line in text.split('\n'):
        if re.match(combined_pattern, line.strip(), re.MULTILINE):
            # Save previous section
            if current_content_lines:
                content = '\n'.join(current_content_lines).strip()
                if content:
                    sections.append({
                        "title": current_title,
                        "content": content,
                        "section_index": section_index,
                    })
                    section_index += 1

            current_title = line.strip()
            current_content_lines = []
        else:
            current_content_lines.append(line)

    # Save last section
    if current_content_lines:
        content = '\n'.join(current_content_lines).strip()
        if content:
            sections.append({
                "title": current_title,
                "content": content,
                "section_index": section_index,
            })

    # If no sections found, return entire text as one section
    if not sections:
        sections = [{
            "title": "Full Document",
            "content": text,
            "section_index": 0,
        }]

    logger.info(f"Split text into {len(sections)} sections")
    return sections


def parse_contract(raw_text: str) -> dict[str, Any]:
    """
    Full parsing pipeline: clean → section → return structured result.

    Returns:
        dict with keys: cleaned_text, sections, char_count, section_count
    """
    cleaned = clean_text(raw_text)
    sections = split_into_sections(cleaned)

    result = {
        "cleaned_text": cleaned,
        "sections": sections,
        "char_count": len(cleaned),
        "section_count": len(sections),
    }

    logger.info(f"Parsed contract: {result['char_count']} chars, {result['section_count']} sections")
    return result
