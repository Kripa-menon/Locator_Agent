import re


def looks_auto_id(s: str):
    if not s:
        return False
    # heuristics: long numeric, hex, or with many dashes
    if re.match(r'^[0-9]{6,}$', s):
        return True
    if re.match(r'^[0-9a-fA-F]{8,}$', s):
        return True
    if len(s) > 30:
        return True
    return False


class LocatorService:
    def __init__(self):
        pass

    def rank_element(self, el: dict):
        # el: dict with tag, outerHTML, id, name, classes, aria, placeholder
        candidates = []
        # 1. id
        if el.get('id') and not looks_auto_id(el.get('id')):
            val = el['id']
            candidates.append({'type': 'css', 'value': f"#{val}", 'reason': 'id', 'stability': 'High'})
        elif el.get('id'):
            candidates.append({'type': 'css', 'value': f"#{el['id']}", 'reason': 'id (looks auto-generated)', 'stability': 'Low'})

        # 2. data-testid / data-test / data-qa
        outer = el.get('outerHTML','')
        m = re.search(r"data-(testid|test|qa)=[\'\"]([^\'\"]+)[\'\"]", outer)
        if m:
            attr = m.group(1)
            v = m.group(2)
            candidates.append({'type': 'css', 'value': f"[data-{attr}='{v}']", 'reason': f'data-{attr}', 'stability': 'High'})

        # 3. name
        if el.get('name'):
            candidates.append({'type': 'css', 'value': f"[name='{el['name']}']", 'reason': 'name', 'stability': 'High'})

        # 4. aria-label / placeholder
        if el.get('aria'):
            candidates.append({'type': 'css', 'value': f"[aria-label='{el['aria']}']", 'reason': 'aria-label', 'stability': 'Medium'})
        if el.get('placeholder'):
            candidates.append({'type': 'css', 'value': f"[placeholder='{el['placeholder']}']", 'reason': 'placeholder', 'stability': 'Medium'})

        # 5. short css using tag + class
        classes = (el.get('classes') or '').strip()
        if classes:
            import re


            def looks_auto_id(s: str) -> bool:
                if not s:
                    return False
                s = s.strip()
                # common auto-generated heuristics
                # long numeric (timestamps, counters)
                if re.match(r'^\d{6,}$', s):
                    return True
                # UUID/GUID
                if re.match(r'^[0-9a-fA-F]{8}-[0-9a-fA-F\-]{8,}$', s):
                    return True
                # long hex-ish
                if re.match(r'^[0-9a-fA-F]{8,}$', s):
                    return True
                # many dashes or very long
                if s.count('-') >= 3 or len(s) > 30:
                    return True
                # framework prefixes
                if re.search(r'ember|react|ng-|mui-|ant-', s, re.I):
                    return True
                return False


            def _escape_attr(v: str) -> str:
                if v is None:
                    return ''
                return v.replace("'", "\\'")


            class LocatorService:
                def __init__(self):
                    pass

                def _short_css_from_attrs(self, tag: str, outer: str, el: dict):
                    # prefer data-* attributes
                    m = re.search(r"data-(testid|test|qa|eid)=[\'\"]([^\'\"]+)[\'\"]", outer)
                    if m:
                        return f"[data-{m.group(1)}='{_escape_attr(m.group(2))}']", f"data-{m.group(1)}"
                    # name
                    if el.get('name'):
                        return f"{tag}[name='{_escape_attr(el.get('name'))}']", 'name'
                    # id if not auto
                    if el.get('id') and not looks_auto_id(el.get('id')):
                        return f"#{_escape_attr(el.get('id'))}", 'id'
                    # aria or placeholder
                    if el.get('aria'):
                        return f"{tag}[aria-label='{_escape_attr(el.get('aria'))}']", 'aria-label'
                    if el.get('placeholder'):
                        return f"{tag}[placeholder='{_escape_attr(el.get('placeholder'))}']", 'placeholder'
                    # class (use first meaningful class)
                    classes = (el.get('classes') or '').strip()
                    if classes:
                        parts = [c for c in classes.split() if len(c) > 1]
                        if parts:
                            return f"{tag}.{parts[0]}", 'class'
                    return None, None

                def _xpath_using_text(self, tag: str, outer: str):
                    # try to extract visible text within element
                    m = re.search(r'>([^<]{1,120})<', outer)
                    if m:
                        text = m.group(1).strip()
                        if len(text) > 0 and len(text) < 120:
                            # use normalize-space and equals first, fallback to contains
                            esc = text.replace("'", "\\'")
                            return f"//{tag}[normalize-space()='{esc}']", 'text-equals'
                    return None, None

                def rank_element(self, el: dict):
                    # el: dict with tag, outerHTML, id, name, classes, aria, placeholder
                    candidates = []
                    tag = (el.get('tag') or 'div').lower()
                    outer = el.get('outerHTML', '')

                    # 1. data-test-like attributes (High)
                    m = re.search(r"data-(testid|test|qa|eid)=[\'\"]([^\'\"]+)[\'\"]", outer)
                    if m:
                        attr = m.group(1)
                        v = _escape_attr(m.group(2))
                        candidates.append({'type': 'css', 'value': f"[data-{attr}='{v}']", 'reason': f'data-{attr}', 'stability': 'High'})

                    # 2. id (skip if looks auto-generated)
                    if el.get('id'):
                        if not looks_auto_id(el.get('id')):
                            candidates.append({'type': 'css', 'value': f"#{_escape_attr(el.get('id'))}", 'reason': 'id', 'stability': 'High'})
                        else:
                            candidates.append({'type': 'css', 'value': f"#{_escape_attr(el.get('id'))}", 'reason': 'id (looks auto-generated)', 'stability': 'Low'})

                    # 3. name
                    if el.get('name'):
                        candidates.append({'type': 'css', 'value': f"{tag}[name='{_escape_attr(el.get('name'))}']", 'reason': 'name', 'stability': 'High'})

                    # 4. aria-label / placeholder
                    if el.get('aria'):
                        candidates.append({'type': 'css', 'value': f"{tag}[aria-label='{_escape_attr(el.get('aria'))}']", 'reason': 'aria-label', 'stability': 'Medium'})
                    if el.get('placeholder'):
                        candidates.append({'type': 'css', 'value': f"{tag}[placeholder='{_escape_attr(el.get('placeholder'))}']", 'reason': 'placeholder', 'stability': 'Medium'})

                    # 5. short CSS from smart attr selection
                    s, reason = self._short_css_from_attrs(tag, outer, el)
                    if s:
                        candidates.append({'type': 'css', 'value': s, 'reason': f'short css ({reason})', 'stability': 'High' if reason in ('data-testid','name','id','data-test','data-qa','data-eid') else 'Medium'})

                    # 6. xpath using visible text
                    xp, xp_reason = self._xpath_using_text(tag, outer)
                    if xp:
                        candidates.append({'type': 'xpath', 'value': xp, 'reason': xp_reason, 'stability': 'Medium'})

                    # 7. xpath using attributes as fallback
                    # prefer data-test/name/id attributes
                    if el.get('id'):
                        candidates.append({'type': 'xpath', 'value': f"//{tag}[@id='{_escape_attr(el.get('id'))}']", 'reason': 'xpath by id', 'stability': 'High' if not looks_auto_id(el.get('id')) else 'Low'})
                    if el.get('name'):
                        candidates.append({'type': 'xpath', 'value': f"//{tag}[@name='{_escape_attr(el.get('name'))}']", 'reason': 'xpath by name', 'stability': 'High'})

                    # 8. class-based xpath
                    classes = (el.get('classes') or '').strip()
                    if classes:
                        first = classes.split()[0]
                        candidates.append({'type': 'css', 'value': f"{tag}.{first}", 'reason': 'tag + class', 'stability': 'Medium'})
                        candidates.append({'type': 'xpath', 'value': f"//{tag}[contains(concat(' ', normalize-space(@class), ' '), ' {first} ')]", 'reason': 'xpath by class', 'stability': 'Medium'})

                    # final fallback: short positional xpath (fragile)
                    candidates.append({'type': 'xpath', 'value': f"(//{tag})[1]", 'reason': 'positional fallback', 'stability': 'Low'})

                    # Initialize match_count placeholder
                    for c in candidates:
                        c['match_count'] = None

                    result = {'best': candidates[0] if candidates else None, 'alternatives': candidates[1:], 'raw': el}
                    return result
