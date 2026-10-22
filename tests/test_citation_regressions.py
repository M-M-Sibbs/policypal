from pathlib import Path

import pytest

from app.chunking import chunk_document
from app.citations import build_citations, snippet_is_verbatim
from app.generator import split_sentences
from app.parsing import parse_document
from app.vectorstore import Hit
from .conftest import FakeGenerator
from .test_rag_components import make_hit


def policy_hit(filename, section):
    chunks = chunk_document(parse_document(Path('data/policies') / filename))
    return Hit(next(c for c in chunks if c.section == section), similarity=0.9)


def test_post_sentence_marker_stays_with_its_claim():
    assert split_sentences('First fact. [1] Second fact. [2]') == ['First fact. [1]', 'Second fact. [2]']


def test_expense_card_quotes_applicable_approval_band():
    hit = policy_hit('POL-06_travel_and_expense.pdf', 'Approval Chain')
    answer = 'A $3,000 claim needs approval by your manager and then the department head. [1]'
    card = build_citations(answer, [hit]).citations[0]
    assert 'Over $1,000 and up to $5,000' in card['snippet']
    assert 'manager and then the department head' in card['snippet']
    assert 'CEO' not in card['snippet']
    assert snippet_is_verbatim(card['snippet'], hit.chunk.text)
    saved_answer = 'The claim must be approved by the employee’s manager and then by the department head. [1]'
    assert 'Over $1,000 and up to $5,000' in build_citations(saved_answer, [hit]).citations[0]['snippet']


def test_late_list_item_keeps_governing_context_without_losing_item():
    text = 'The following equipment is prohibited:\n' + 'ordinary equipment;\n' * 30 + 'radio transmitters;'
    snippet = build_citations('Radio transmitters are prohibited [1].', [make_hit(1, text)]).citations[0]['snippet']
    assert 'prohibited:' in snippet and 'radio transmitters;' in snippet
    assert snippet_is_verbatim(snippet, text)


def test_reused_marker_displays_evidence_for_each_sentence():
    text = 'Employees receive 20 days of PTO.\n' + 'Other details.\n' * 30 + 'Report incidents within one hour.'
    answer = 'Employees receive 20 PTO days [1]. Report incidents within one hour [1].'
    snippet = build_citations(answer, [make_hit(1, text)]).citations[0]['snippet']
    assert '20 days' in snippet and 'within one hour' in snippet
    assert snippet_is_verbatim(snippet, text)


def test_compound_claim_displays_both_supporting_passages():
    text = 'Employees must use company laptops for work.\nUnrelated material.\nPersonal phones may use only the managed email app.'
    answer = 'Employees must use company laptops for work, and personal phones may use only the managed email app [1].'
    snippet = build_citations(answer, [make_hit(1, text)]).citations[0]['snippet']
    assert 'company laptops' in snippet and 'managed email app' in snippet


def test_each_marker_is_scored_against_its_own_claim():
    expense = policy_hit('POL-06_travel_and_expense.pdf', 'Approval Chain')
    other = make_hit(2, 'Claims from the CFO are approved by the CEO.')
    answer = ('Your manager and then department head approve the claim. [1] '
              'Claims from the CFO are approved by the CEO. [2]')
    snippet = build_citations(answer, [expense, other]).citations[0]['snippet']
    assert 'Over $1,000 and up to $5,000' in snippet and 'CEO' not in snippet


def test_torrent_card_keeps_prohibition_and_named_item():
    hit = policy_hit('POL-08_acceptable_use_of_it.md', 'Prohibited Software')
    card = build_citations('Torrent clients are prohibited on company devices. [1]', [hit]).citations[0]
    assert 'torrent clients' in card['snippet']
    assert 'prohibited on company devices' in card['snippet']
    assert snippet_is_verbatim(card['snippet'], hit.chunk.text)


def test_table_evidence_keeps_column_header():
    hit = make_hit(1, 'Plan | Annual allowance\nBasic | $100\nPremium | $250')
    snippet = build_citations('The Premium plan allows $250 annually [1].', [hit]).citations[0]['snippet']
    assert 'Annual allowance' in snippet and 'Premium | $250' in snippet
    assert snippet_is_verbatim(snippet, hit.chunk.text)


@pytest.mark.parametrize('answer', [
    'You may carry over five days [1]. Acme also guarantees a $10000 bonus [99].',
    'You may carry over five days [1]. Acme also guarantees a $10000 bonus.',
    'You may carry over five days [1][99].',
    'You may carry over five days [1, 999].',
    'You may carry over five days [1]. Bonuses are guaranteed [x].',
])
def test_invalid_or_uncited_claims_are_never_cleaned_into_accepted_answers(make_client, answer):
    generator = FakeGenerator(answer)
    body = make_client(generator).post('/chat', json={'question': 'How many PTO days can I carry over?'}).get_json()
    assert body['refused'] and body['citations'] == []
    assert 'bonus' not in body['answer'].lower()
    assert len(generator.calls) == 2


def test_invalid_answer_can_recover_without_retaining_unsupported_claim(make_client):
    generator = FakeGenerator('Five days [1]. Bonus [99].', 'Up to five PTO days carry over [1].')
    body = make_client(generator).post('/chat', json={'question': 'How many PTO days can I carry over?'}).get_json()
    assert body['status'] == 'answered' and 'Bonus' not in body['answer']
    assert len(generator.calls) == 2
