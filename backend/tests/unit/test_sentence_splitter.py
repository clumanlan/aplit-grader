from aplit_grader.services.sentence_splitter import split_into_sentences


def test_splits_two_simple_sentences_with_exact_offsets():
    essay_text = "Gatsby believed in the green light. He never gave up hope."

    sentences = split_into_sentences(essay_text)

    assert len(sentences) == 2
    assert sentences[0].text == "Gatsby believed in the green light."
    assert sentences[1].text == "He never gave up hope."
    for sentence in sentences:
        assert essay_text[sentence.span_start : sentence.span_end] == sentence.text


def test_indices_are_sequential_and_zero_based():
    essay_text = "First sentence. Second sentence. Third sentence."

    sentences = split_into_sentences(essay_text)

    assert [s.index for s in sentences] == [0, 1, 2]


def test_a_comma_heavy_run_on_sentence_stays_one_sentence():
    # This is the exact case a naive punctuation/comma split would mangle — a real
    # sentence tokenizer must only break on actual sentence-ending punctuation.
    essay_text = (
        "Gatsby, who had reinvented himself from nothing, who had built a mansion, "
        "and who had waited five years, still believed in the green light."
    )

    sentences = split_into_sentences(essay_text)

    assert len(sentences) == 1
    assert sentences[0].text == essay_text


def test_offsets_are_exact_across_a_multi_paragraph_essay():
    essay_text = "Paragraph one, sentence one. Paragraph one, sentence two.\n\nParagraph two starts here. It has two sentences."

    sentences = split_into_sentences(essay_text)

    assert len(sentences) == 4
    for sentence in sentences:
        assert essay_text[sentence.span_start : sentence.span_end] == sentence.text
