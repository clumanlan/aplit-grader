from dataclasses import dataclass
from functools import lru_cache

import spacy
from spacy.language import Language


@dataclass(frozen=True)
class SplitSentence:
    index: int
    span_start: int
    span_end: int
    text: str


@lru_cache(maxsize=1)
def _nlp() -> Language:
    nlp = spacy.blank("en")
    nlp.add_pipe("sentencizer")
    return nlp


def split_into_sentences(essay_text: str) -> list[SplitSentence]:
    doc = _nlp()(essay_text)
    return [
        SplitSentence(
            index=index,
            span_start=sent.start_char,
            span_end=sent.end_char,
            text=sent.text,
        )
        for index, sent in enumerate(doc.sents)
    ]
