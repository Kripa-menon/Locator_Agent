import pytest
from app.locator import LocatorService, looks_auto_id, select_best_candidate


def test_auto_id_detection():
    assert looks_auto_id('1234567890')
    assert looks_auto_id('550e8400-e29b-41d4-a716-446655440000')
    assert looks_auto_id('react-xyz-123')
    assert not looks_auto_id('login-button')


def test_rank_element_basic():
    svc = LocatorService()
    el = {
        'tag': 'BUTTON',
        'outerHTML': '<button id="submit" data-testid="login-submit">Log in</button>',
        'id': 'submit',
        'classes': 'btn primary',
        'aria': None,
        'placeholder': None,
        'name': None,
    }
    r = svc.rank_element(el)
    assert r['best'] is not None
    assert any(
        'data-test' in (a.get('reason') or '') or 'data-testid' in (a.get('reason') or '') or a.get('value', '').startswith('[data-')
        for a in ([r['best']] + r['alternatives'])
    )


def test_select_best_candidate_prefers_unique_match():
    candidates = [
        {'type': 'css', 'value': 'a.btn', 'reason': 'short css (class)', 'stability': 'Medium', 'match_count': 3},
        {'type': 'xpath', 'value': "//a[normalize-space()='Enroll Yourself']", 'reason': 'text-equals', 'stability': 'Medium', 'match_count': 1},
    ]

    best = select_best_candidate(candidates)

    assert best is not None
    assert best['type'] == 'xpath'
    assert best['match_count'] == 1


def test_select_best_candidate_prefers_id_over_xpath_when_available():
    candidates = [
        {'type': 'xpath', 'value': "(//input)[1]", 'reason': 'positional fallback', 'stability': 'Low', 'match_count': 1},
        {'type': 'xpath', 'value': "//input[@id='dateOfBirthInput']", 'reason': 'xpath by id', 'stability': 'High', 'match_count': 1},
        {'type': 'css', 'value': "#dateOfBirthInput", 'reason': 'id', 'stability': 'High', 'match_count': 1},
    ]

    best = select_best_candidate(candidates)

    assert best is not None
    assert best['value'] == '#dateOfBirthInput'
    assert best['reason'] == 'id'


def test_select_best_candidate_prefers_semantic_text_over_positional_fallback():
    candidates = [
        {'type': 'xpath', 'value': '(//a)[1]', 'reason': 'positional fallback', 'stability': 'Low', 'match_count': 1},
        {'type': 'xpath', 'value': "//a[normalize-space()='edit']", 'reason': 'text-equals', 'stability': 'Medium', 'match_count': 10},
    ]

    best = select_best_candidate(candidates)

    assert best is not None
    assert best['value'] == "//a[normalize-space()='edit']"
    assert 'positional fallback' not in (best.get('reason') or '').lower()


def test_rank_element_deduplicates_same_selector_values():
    svc = LocatorService()
    el = {
        'tag': 'INPUT',
        'outerHTML': '<input id="firstName" name="firstName" type="text" />',
        'id': 'firstName',
        'name': 'firstName',
        'classes': '',
        'aria': None,
        'placeholder': None,
    }

    ranked = svc.rank_element(el)
    values = [c.get('value') for c in [ranked['best']] + ranked['alternatives'] if c]

    assert values.count('#firstName') == 1
    assert len(set(values)) == len(values)
