from eval.run import score_response


QUESTION = {'should_refuse': False, 'gold_facts': ['department head'], 'gold_doc_ids': ['POL-06'],
            'required_answer_groups': [['manager'], ['department head']],
            'required_evidence_groups': [['$1,000'], ['$5,000'], ['manager'], ['department head']]}


def response(answer='Manager then department head [1].', snippet='Claims from department heads are approved by the CFO.'):
    return {'status': 'answered', 'refused': False, 'answer': answer,
            'provider': 'groq:model', 'generation': {'mode': 'llm', 'failures': []},
            'citations': [{'id': 1, 'document_id': 'POL-06', 'chunk_id': 'c1', 'snippet': snippet}]}


def test_correct_document_with_wrong_displayed_rule_fails_evidence_proxy():
    result = score_response(QUESTION, 200, response(), {'c1': response()['citations'][0]['snippet']})
    assert result['snippet_verbatim'] is True
    assert result['evidence_complete_proxy'] is False
    assert result['citation_correct_proxy'] is False


def test_irrelevant_answer_does_not_pass_behavior_just_because_200():
    result = score_response(QUESTION, 200, response('The sky is blue [1].'))
    assert not result['behavior_pass']


def test_invalid_marker_or_uncited_claim_fails_format():
    for answer in ['Manager [1]. Bonus [99].', 'Manager [1]. Bonus guaranteed.']:
        result = score_response(QUESTION, 200, response(answer))
        assert result['citation_format_valid'] is False


def test_sentence_support_uses_its_own_citation():
    body = response('Employees get five days [1]. Managers approve claims [2].', 'Managers approve claims.')
    body['citations'].append({'id': 2, 'document_id': 'POL-06', 'chunk_id': 'c2', 'snippet': 'Employees get five days.'})
    assert score_response(QUESTION, 200, body)['displayed_support_proxy'] is False


def test_strict_mode_rejects_degraded_and_unknown_coverage():
    body = response(snippet='Over $1,000 and up to $5,000: manager and then department head.')
    body['generation']['mode'] = 'degraded'
    body['provider'] = 'extractive:offline'
    assert not score_response(QUESTION, 200, body, strict_llm=True)['strict_llm_pass']
    body.pop('generation')
    body['provider'] = 'groq:model'
    assert not score_response(QUESTION, 200, body, strict_llm=True)['strict_llm_pass']


def test_missing_evidence_snapshot_is_unknown_not_a_fabricated_pass():
    assert score_response(QUESTION, 200, response())['snippet_verbatim'] is None


def test_incorrect_refusal_and_service_error_fail():
    body = {'status': 'insufficient_evidence', 'refused': True, 'answer': 'Not covered.', 'citations': []}
    assert not score_response(QUESTION, 200, body)['behavior_pass']
    assert not score_response({'should_refuse': True, 'gold_facts': [], 'gold_doc_ids': []}, 502, body)['behavior_pass']
