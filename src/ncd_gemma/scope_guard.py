"""Reject answers whose evidence omits an explicit clinical scope in the query.

These are conservative lexical gates. They do not establish entailment; the
ordinary evidence reviewer still has to approve the answer after they pass.
"""
from __future__ import annotations

import re


def scope_mismatch(question: str, answer: str, citations: list, sources: dict) -> str | None:
    cited = [sources[c.source_id]['text'].casefold() for c in citations]
    if not cited:
        return None
    query = question.casefold()

    # Medication instructions cannot be transferred from one named drug to
    # another. Only Latin drug names in a dosing/missed-dose question are
    # checked; the guard declines to guess Thai transliterations or synonyms.
    if re.search(r'ลืม(?:กิน|รับประทาน)|ขนาดยา|เพิ่มยา|กินยา', question):
        tokens = re.findall(r'(?<![a-z])[a-z][a-z-]{4,}(?![a-z])', query)
        for token in tokens:
            if token not in {'daily', 'every', 'after', 'before', 'about', 'medicine'} and not any(token in text for text in cited):
                return 'The question names a medication absent from all selected evidence. Do not transfer dosing or missed-dose advice from another drug.'

    # A population-specific BMI table has a different classification from
    # the nearby general Asian-population table in the same guideline.
    if (re.search(r'เนโฟรติก|nephrotic', query) and 'bmi' in query
            and not any('เนโฟรติก' in text or 'nephrotic' in text for text in cited)):
        return 'The question specifies nephrotic syndrome, but the selected evidence does not cover that population.'

    # A general snack allowance for children is not a joint diabetes/CKD
    # recommendation. Require both disease scopes somewhere in the cited
    # evidence pack before releasing a quantified food answer.
    dietary = any(word in question for word in ('อาหาร', 'ของว่าง', 'กิน', 'พลังงาน', 'คาร์บ'))
    quantified = bool(re.search(r'\d', re.sub(r'\[S\d+\]', '', answer)))
    if dietary and quantified and 'เบาหวาน' in question and re.search(r'โรคไต|ไตเรื้อรัง', question):
        body = '\n'.join(cited)
        if not ('เบาหวาน' in body or re.search(r'\bdiabet', body)) or not ('โรคไต' in body or re.search(r'\bckd\b|\bkidney\b|\brenal\b', body)):
            return 'The answer gives a food quantity for diabetes with kidney disease, but the selected evidence does not cover both disease scopes.'
    return None
