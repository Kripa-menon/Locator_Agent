import re


def looks_auto_id(s: str) -> bool:
    if not s:
        return False
    s = s.strip()
    if re.match(r'^[0-9]{6,}$', s):
        return True
    if re.match(r'^[0-9a-fA-F]{8,}$', s):
        return True
    if re.match(r'^[0-9a-fA-F]{8}-[0-9a-fA-F\-]{8,}$', s):
        return True
    if s.count('-') >= 3 or len(s) > 30:
        return True
    if re.search(r'ember|react|ng-|mui-|ant-', s, re.I):
        return True
    return False


def _escape_attr(v: str) -> str:
    if v is None:
        return ''
    return str(v).replace("'", "\\'")


def select_best_candidate(candidates):
    def sort_key(c):
        if not c:
            return (1, 1, 1, 1, 1, 1)
        stability_rank = {'High': 0, 'Medium': 1, 'Low': 2}.get(c.get('stability', 'Low'), 2)
        match_count = c.get('match_count')
        reason = (c.get('reason') or '').lower()
        value = str(c.get('value') or '')
        is_unique_match = 0 if match_count == 1 else 1
        is_positive_count = 0 if isinstance(match_count, int) and match_count > 0 else 1
        has_text_signal = 0 if ('text' in reason or 'normalize-space' in value or 'label' in reason or 'placeholder' in reason) else 1
        prefers_xpath = 0 if c.get('type') == 'xpath' and has_text_signal == 0 else 1
        return (is_unique_match, is_positive_count, has_text_signal, prefers_xpath, stability_rank, 0 if c.get('type') == 'xpath' else 1)

    filtered = [c for c in candidates if c]
    if not filtered:
        return None
    return sorted(filtered, key=sort_key)[0]


class LocatorService:
    def __init__(self):
        pass

    def _short_css_from_attrs(self, tag: str, outer: str, el: dict):
        m = re.search(r"data-(testid|test|qa|eid)=[\'\"]([^\'\"]+)[\'\"]", outer)
        if m:
            return f"[data-{m.group(1)}='{_escape_attr(m.group(2))}']", f"data-{m.group(1)}"
        if el.get('name'):
            return f"{tag}[name='{_escape_attr(el.get('name'))}']", 'name'
        if el.get('id') and not looks_auto_id(el.get('id')):
            return f"#{_escape_attr(el.get('id'))}", 'id'
        if el.get('aria'):
            return f"{tag}[aria-label='{_escape_attr(el.get('aria'))}']", 'aria-label'
        if el.get('placeholder'):
            return f"{tag}[placeholder='{_escape_attr(el.get('placeholder'))}']", 'placeholder'
        classes = (el.get('classes') or '').strip()
        if classes:
            parts = [c for c in classes.split() if len(c) > 1]
            if parts:
                return f"{tag}.{parts[0]}", 'class'
        return None, None

    def _xpath_using_text(self, tag: str, outer: str):
        m = re.search(r'>([^<]{1,120})<', outer)
        if m:
            text = m.group(1).strip()
            if 0 < len(text) < 120:
                esc = text.replace("'", "\\'")
                return f"//{tag}[normalize-space()='{esc}']", 'text-equals'
        return None, None

    def rank_element(self, el: dict):
        # handle None gracefully
        if not el:
            return {'best': None, 'alternatives': [], 'raw': None}

        candidates = []
        tag = (el.get('tag') or 'div').lower()
        outer = el.get('outerHTML', '')

        # data-test-like attributes
        m = re.search(r"data-(testid|test|qa|eid)=[\'\"]([^\'\"]+)[\'\"]", outer)
        if m:
            attr = m.group(1)
            v = _escape_attr(m.group(2))
            candidates.append({'type': 'css', 'value': f"[data-{attr}='{v}']", 'reason': f'data-{attr}', 'stability': 'High'})

        # id
        if el.get('id'):
            if not looks_auto_id(el.get('id')):
                candidates.append({'type': 'css', 'value': f"#{_escape_attr(el.get('id'))}", 'reason': 'id', 'stability': 'High'})
            else:
                candidates.append({'type': 'css', 'value': f"#{_escape_attr(el.get('id'))}", 'reason': 'id (looks auto-generated)', 'stability': 'Low'})

        # name
        if el.get('name'):
            candidates.append({'type': 'css', 'value': f"{tag}[name='{_escape_attr(el.get('name'))}']", 'reason': 'name', 'stability': 'High'})

        # aria / placeholder
        if el.get('aria'):
            candidates.append({'type': 'css', 'value': f"{tag}[aria-label='{_escape_attr(el.get('aria'))}']", 'reason': 'aria-label', 'stability': 'Medium'})
        if el.get('placeholder'):
            candidates.append({'type': 'css', 'value': f"{tag}[placeholder='{_escape_attr(el.get('placeholder'))}']", 'reason': 'placeholder', 'stability': 'Medium'})

        # short css
        s, reason = self._short_css_from_attrs(tag, outer, el)
        if s:
            candidates.append({'type': 'css', 'value': s, 'reason': f'short css ({reason})', 'stability': 'High' if reason in ('data-testid', 'name', 'id', 'data-test', 'data-qa', 'data-eid') else 'Medium'})

        # xpath using visible text
        xp, xp_reason = self._xpath_using_text(tag, outer)
        if xp:
            candidates.append({'type': 'xpath', 'value': xp, 'reason': xp_reason, 'stability': 'Medium'})

        # xpath fallbacks
        if el.get('id'):
            candidates.append({'type': 'xpath', 'value': f"//{tag}[@id='{_escape_attr(el.get('id'))}']", 'reason': 'xpath by id', 'stability': 'High' if not looks_auto_id(el.get('id')) else 'Low'})
        if el.get('name'):
            candidates.append({'type': 'xpath', 'value': f"//{tag}[@name='{_escape_attr(el.get('name'))}']", 'reason': 'xpath by name', 'stability': 'High'})

        # class-based
        classes = (el.get('classes') or '').strip()
        if classes:
            first = classes.split()[0]
            candidates.append({'type': 'css', 'value': f"{tag}.{first}", 'reason': 'tag + class', 'stability': 'Medium'})
            candidates.append({'type': 'xpath', 'value': f"//{tag}[contains(concat(' ', normalize-space(@class), ' '), ' {first} ')]", 'reason': 'xpath by class', 'stability': 'Medium'})

        # positional fallback
        candidates.append({'type': 'xpath', 'value': f"(//{tag})[1]", 'reason': 'positional fallback', 'stability': 'Low'})

        for c in candidates:
            c['match_count'] = None

        result = {'best': candidates[0] if candidates else None, 'alternatives': candidates[1:], 'raw': el}
        return result
