import pytest
from app.locator import LocatorService, looks_auto_id


def test_auto_id_detection():
    assert looks_auto_id('1234567890')
    assert looks_auto_id('550e8400-e29b-41d4-a716-446655440000')
    assert looks_auto_id('react-xyz-123')
    assert not looks_auto_id('login-button')


def test_rank_element_basic():
    svc = LocatorService()
    el = {'tag':'BUTTON','outerHTML':'<button id="submit" data-testid="login-submit">Log in</button>','id':'submit','classes':'btn primary','aria':None,'placeholder':None,'name':None}
    r = svc.rank_element(el)
    assert r['best'] is not None
    assert any('data-test' in (a.get('reason') or '') or 'data-testid' in (a.get('reason') or '') or a.get('value','').startswith('[data-') for a in ([r['best']] + r['alternatives']))
*** End Patch