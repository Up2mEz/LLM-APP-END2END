"""Evidence-linked review; schema/provenance checks do not prove entailment."""
from __future__ import annotations

import re

from pydantic import Field, model_validator

from .schemas import Nonblank, StrictModel
from .json_protocol import load_json


from .prompts import REVIEW_PROMPT
VERIFY_SYSTEM_PROMPT = REVIEW_PROMPT


def json_text(content: str) -> str:
    text = (content or "").strip()
    if text.startswith("```") and text.endswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)[:-3].strip()
    return text


def misses_explicit_quantity(question: str, answer: str) -> bool:
    """A narrow completeness check, not a check that the reported value is right."""
    # The substring กี่ also occurs inside เกี่ยว(ข้อง); that is not a
    # quantity question. Grades such as III B are quantities in guideline
    # recommendation tables even though they contain no Arabic digits.
    if not (re.search(r'(?<!เ)กี่', question) or 'เท่าไร' in question or 'เท่าไหร่' in question):
        return False
    # Source IDs are not quantities. Also recognise ordinary Thai number words.
    plain = re.sub(r"\[S\d+(?:\s*[,;]\s*S\d+)*\]", "", answer)
    # Repeating a year from the question is not an answer to a requested amount.
    plain = re.sub(r'(?:ปี\s*(?:พ\.?\s*ศ\.?\s*)?)\d{4}', '', plain)
    if re.search(r'ระดับ(?:คำแนะนำ|หลักฐาน)', question) and re.search(r'(?<![A-Za-z])[IVX]+\s+[A-D](?![A-Za-z])', plain):
        return False
    return not re.search(r"[0-9๐-๙]|ศูนย์|หนึ่ง|สอง|สาม|สี่|ห้า|หก|เจ็ด|แปด|เก้า|สิบ|ร้อย|พัน|หมื่น|แสน|ล้าน|ครึ่ง", plain)


class EvidenceCheck(StrictModel):
    requirement: Nonblank = Field(max_length=500)
    covered: bool
    answer_quote: str | None = Field(max_length=1000)
    source_id: str = Field(max_length=3)
    evidence_quote: str = Field(max_length=1800)


class EvidenceReview(StrictModel):
    checks: list[EvidenceCheck] = Field(min_length=1, max_length=12)
    supported: bool
    reason: Nonblank = Field(max_length=1000)

    @model_validator(mode="after")
    def consistent(self):
        if self.supported and not all(c.covered for c in self.checks):
            raise ValueError("An uncovered requirement cannot be approved")
        return self


class LineCheck(StrictModel):
    requirement: Nonblank = Field(max_length=500)
    covered: bool
    source_id: str = Field(max_length=3)
    answer_quote: str | None = Field(default=None, max_length=1000)
    start_line: int = Field(ge=0)
    end_line: int = Field(ge=0)


class LineReview(StrictModel):
    checks: list[LineCheck] = Field(min_length=1, max_length=12)
    supported: bool
    reason: str = Field(max_length=1000)

    @model_validator(mode="after")
    def consistent(self):
        if self.supported and not all(c.covered for c in self.checks):
            raise ValueError("An uncovered requirement cannot be approved")
        return self


def parse_review(message: dict, answer: str, sources: dict, claims: dict | None = None) -> EvidenceReview:
    if message.get("tool_calls"):
        raise ValueError("Review must not call tools")
    content = json_text(message.get("content") or "")
    import json
    from .evidence import line_quote, span_range
    raw = load_json(content)
    if isinstance(raw, dict):
        for check in raw.get('checks', []):
            if isinstance(check,dict) and 'span_id' in check:
                sid=check.pop('span_id')
                check['span_ids']=[sid] if sid else []
            if isinstance(check,dict) and 'claim_id' in check:
                cid = check.pop('claim_id')
                if check.get('covered'):
                    if not claims or cid not in claims or check.get('source_id') != claims[cid]['source_id']:
                        raise ValueError('Review must select an existing claim_id with its original source_id')
                    check['answer_quote'] = claims[cid]['text']
                else:
                    check['answer_quote'] = ''
            if isinstance(check, dict) and 'span_ids' in check:
                if 'answer_quote' not in check:
                    raise ValueError('Passage reviews require answer_quote')
                spans = check.pop('span_ids')
                if check.get('covered'):
                    if check.get('source_id') not in sources:
                        raise ValueError('Unknown review source ID')
                    start, end = span_range(sources[check['source_id']], spans)
                    check.update(start_line=start, end_line=end)
                else:
                    check.update(start_line=0, end_line=0)
    if isinstance(raw, dict) and any("start_line" in c for c in raw.get("checks", []) if isinstance(c, dict)):
        review = LineReview.model_validate(raw)
        if review.supported:
            for check in review.checks:
                if check.source_id not in sources:
                    raise ValueError("Unknown review source ID")
                line_quote(sources[check.source_id], check.start_line, check.end_line)
                if check.answer_quote is not None:
                    norm = lambda x: re.sub(r'\s+', '', x)
                    if not norm(check.answer_quote) or norm(check.answer_quote) not in norm(answer):
                        raise ValueError('answer_quote must be a verbatim substring of the answer')
        return review
    review = EvidenceReview.model_validate(raw)
    # A negative verdict releases no answer, so do not spend another model call
    # repairing unused support excerpts from its other checks.
    if not review.supported:
        return review
    normalize = lambda text: re.sub(r"\s+", "", text)
    for check in review.checks:
        if not check.covered:
            continue
        if (not isinstance(check.answer_quote, str) or not normalize(check.answer_quote)
                or normalize(check.answer_quote) not in normalize(answer)):
            raise ValueError("answer_quote must be a short verbatim substring of answer; do not rewrite it")
        if (check.source_id not in sources or len(normalize(check.evidence_quote)) < 8
                or normalize(check.evidence_quote) not in normalize(sources[check.source_id]["text"])):
            raise ValueError("evidence_quote must be a short verbatim substring of the source text; do not rewrite it")
        if not any(char.isalpha() for char in check.evidence_quote):
            raise ValueError("Evidence quote contains only numbers; include its label or unit, or mark covered false")
    return review
