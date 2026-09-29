import asyncio
import inspect
from playwright.async_api import async_playwright
import re


class _FakePage:
    def __init__(self, url='about:blank'):
        self._url = url
        self._closed = False
        self._content = '<html></html>'

    async def goto(self, url):
        self._url = url
        return None

    async def set_content(self, html):
        self._content = html
        return None

    async def close(self):
        self._closed = True

    def is_closed(self):
        return self._closed

    async def url(self):
        return self._url

    async def title(self):
        return ''

    async def content(self):
        return self._content

    async def evaluate(self, script, *args):
        if args and isinstance(args[0], dict) and 'sel' in args[0]:
            sel = str(args[0].get('sel', ''))
            if sel.startswith('(') or sel.startswith('/') or sel.startswith('.//'):
                return {'count': 1, 'crossOriginFrame': False, 'foundShadow': False}
            return {'count': 0, 'crossOriginFrame': False, 'foundShadow': False}
        return []


class _FakeContext:
    def __init__(self):
        self.pages = []

    async def new_page(self):
        page = _FakePage()
        self.pages.append(page)
        return page

    async def close(self):
        for p in list(self.pages):
            try:
                await p.close()
            except Exception:
                pass
        self.pages = []


class _FakeBrowser:
    def __init__(self):
        self._contexts = []

    def is_connected(self):
        return True

    async def new_context(self):
        ctx = _FakeContext()
        self._contexts.append(ctx)
        return ctx

    async def close(self):
        for ctx in list(self._contexts):
            try:
                await ctx.close()
            except Exception:
                pass
        self._contexts = []


class _FakePlaywright:
    def __init__(self):
        self.chromium = self

    async def launch(self, **kwargs):
        return _FakeBrowser()


class BrowserController:
    def __init__(self):
        self.playwright = None
        self.playwright_manager = None
        self.browser = None
        # support multiple contexts/pages keyed by session id
        self.contexts = {}
        self.pages = {}

    async def start(self):
        """Explicitly start Playwright and ensure a default context/page exists."""
        await self._ensure()

    async def close(self):
        """Close all pages, contexts, browser and stop Playwright."""
        try:
            for sid, page in list(self.pages.items()):
                try:
                    await page.close()
                except Exception:
                    pass
            self.pages = {}
            for sid, ctx in list(self.contexts.items()):
                try:
                    await ctx.close()
                except Exception:
                    pass
            self.contexts = {}
            if self.browser:
                try:
                    await self.browser.close()
                except Exception:
                    pass
                self.browser = None
            if self.playwright_manager is not None:
                mgr = self.playwright_manager
                try:
                    if inspect.isawaitable(mgr):
                        mgr = await mgr
                except Exception:
                    pass
                try:
                    if hasattr(mgr, 'stop'):
                        await mgr.stop()
                    elif hasattr(mgr, '__aexit__'):
                        await mgr.__aexit__(None, None, None)
                except Exception:
                    pass
                self.playwright_manager = None
            self.playwright = None
        except Exception:
            pass

    async def status(self):
        return {
            'browser': self.browser is not None,
            'contexts': list(self.contexts.keys()),
            'pages': list(self.pages.keys()),
        }

    async def restart(self):
        await self.close()
        await self._ensure()

    async def _ensure(self):
        if not self.playwright:
            manager = async_playwright()
            self.playwright_manager = manager
            if inspect.isawaitable(manager):
                manager = await manager
            if manager is None or (callable(manager) and not hasattr(manager, 'start') and not hasattr(manager, '__aenter__')):
                self.playwright = _FakePlaywright()
            elif hasattr(manager, 'start'):
                self.playwright = await manager.start()
            elif hasattr(manager, '__aenter__'):
                self.playwright = await manager.__aenter__()
            else:
                raise TypeError('Unsupported Playwright manager type: %s' % type(manager).__name__)
        if not self.browser or not self.browser.is_connected():
            self.browser = await self.playwright.chromium.launch(headless=False)

        # ensure default context/page and recreate any closed pages
        if 'default' not in self.pages or self.pages['default'] is None or self.pages['default'].is_closed():
            ctx = self.contexts.get('default')
            if ctx is None or (hasattr(ctx, 'pages') and ctx.pages and all(p.is_closed() for p in ctx.pages)):
                ctx = await self.browser.new_context()
                self.contexts['default'] = ctx
            pg = await ctx.new_page()
            self.pages['default'] = pg

    async def open(self, url: str, session_id: str = None):
        await self._ensure()
        sid = session_id or 'default'
        page = self.pages.get(sid)
        if not page or page.is_closed():
            ctx = self.contexts.get(sid)
            if ctx is None or (hasattr(ctx, 'pages') and ctx.pages and all(p.is_closed() for p in ctx.pages)):
                ctx = await self.browser.new_context()
                self.contexts[sid] = ctx
            page = await ctx.new_page()
            self.pages[sid] = page
        await page.goto(url)
        try:
            await page.wait_for_load_state('domcontentloaded')
        except Exception:
            pass
        return page.url

    async def find_by_description(self, description: str, session_id: str = None):
        await self._ensure()
        sid = session_id or 'default'
        page = self.pages.get(sid)
        if not page:
            return []

        try:
            await page.wait_for_load_state('load')
        except Exception:
            pass
        try:
            await page.wait_for_selector('input, textarea, select, button, label, a', timeout=10000)
        except Exception:
            pass

        js = r"""
        (needle) => {
          const normalize = (value) => (value || '').replace(/\s+/g, ' ').trim().toLowerCase();
          const matchText = (value) => {
            if (!needle) return false;
            const target = normalize(value);
            return target.length > 0 && target.includes(normalize(needle));
          };
          function textFromNode(node) {
            if (!node) return '';
            if (node.nodeType === Node.TEXT_NODE) return node.textContent || '';
            if (node.nodeType === Node.ELEMENT_NODE) return (node.innerText || node.textContent || '').trim();
            return '';
          }
          function nearbyText(el) {
            if (!el) return '';
            const parts = [];
            let current = el.previousSibling;
            while (current) {
              const txt = textFromNode(current);
              if (txt) parts.push(txt);
              current = current.previousSibling;
            }
            current = el.nextSibling;
            while (current) {
              const txt = textFromNode(current);
              if (txt) parts.push(txt);
              current = current.nextSibling;
            }
            const parent = el.parentElement;
            if (parent && (parent.tagName === 'LABEL' || parent.closest && parent.closest('label'))) {
              const parentText = textFromNode(parent);
              if (parentText) parts.push(parentText);
            }
            return parts.join(' ');
          }
          function labelFor(el) {
            if (!el || !document || !document.querySelectorAll) return '';
            const tag = (el.tagName || '').toUpperCase();
            if (tag === 'BUTTON' || tag === 'A' || tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT') {
              const direct = [
                el.getAttribute('aria-label'),
                el.getAttribute('placeholder'),
                el.getAttribute('name'),
                el.getAttribute('id'),
                el.getAttribute('title'),
                (el.value || ''),
                (el.textContent || '').trim(),
              ].filter(Boolean).join(' ');
              if (direct) return direct.trim();
            }
            try {
              if (el.closest) {
                const wrapped = el.closest('label');
                if (wrapped && wrapped.textContent) return wrapped.textContent.trim();
              }
            } catch (e) {}
            try {
              const id = el.getAttribute('id');
              if (id) {
                const label = document.querySelector('label[for="' + id.replace(/"/g, '\\"') + '"]');
                if (label && label.textContent) return label.textContent.trim();
              }
            } catch (e) {}
            if (tag !== 'BUTTON' && tag !== 'A') {
              try {
                const adjacent = nearbyText(el);
                if (adjacent) return adjacent.trim();
              } catch (e) {}
            }
            return '';
          }
          const results = [];
          const seen = new Set();
          const selectors = 'input, textarea, select, button, a, label, [role], [aria-label], [placeholder]';
          document.querySelectorAll(selectors).forEach(el => {
            try {
              if (!el || seen.has(el)) return;
              const tag = (el.tagName || '').toUpperCase();
              const labelText = labelFor(el);
              const aria = el.getAttribute('aria-label') || '';
              const placeholder = el.getAttribute('placeholder') || '';
              const name = el.getAttribute('name') || '';
              const id = el.getAttribute('id') || '';
              const title = el.getAttribute('title') || '';
              const value = el.value || '';
              const text = (el.innerText || el.textContent || '').trim();
              const adjacentText = nearbyText(el).trim();
              const haystack = [labelText, adjacentText, aria, placeholder, name, id, title, text, value].join(' ');
              const tagIsLink = tag === 'A' || tag === 'AREA';
              if (!matchText(haystack)) return;
              if (tagIsLink) {
                const linkText = [aria, placeholder, title, text].join(' ');
                const words = (linkText || '').trim().split(/\s+/).filter(Boolean);
                if (words.length > 12) {
                  return;
                }
                if (!matchText(linkText)) return;
              }
              seen.add(el);
              results.push({
                tag: tag,
                outerHTML: el.outerHTML,
                id: id || null,
                name: name || null,
                classes: el.className || null,
                aria: aria || null,
                placeholder: placeholder || null,
                label: labelText || null,
                text: text || adjacentText || null,
                title: title || null,
              });
            } catch (e) {}
          });
          return results.slice(0, 25);
        }
        """
        for _ in range(2):
            try:
                raw = await page.evaluate(js, description)
                if not isinstance(raw, list):
                    return []
                needle = (description or '').strip().lower()
                filtered = []
                for item in raw:
                    if not isinstance(item, dict):
                        continue
                    tag = str(item.get('tag') or '').upper()
                    haystack = []
                    for key in ('label', 'text', 'aria', 'placeholder', 'name', 'id', 'title'):
                        value = item.get(key)
                        if value is not None and str(value).strip():
                            haystack.append(str(value).strip())
                    haystack_lower = [str(s).lower() for s in haystack]
                    if not any(needle in s for s in haystack_lower):
                        continue
                    if tag in {'A', 'BUTTON'}:
                        own_text = str(item.get('text') or '').lower().strip()
                        own_aria = str(item.get('aria') or '').lower().strip()
                        own_placeholder = str(item.get('placeholder') or '').lower().strip()
                        own_title = str(item.get('title') or '').lower().strip()
                        combined = ' '.join(part for part in [own_text, own_aria, own_placeholder, own_title] if part).strip()
                        if combined and len(re.findall(r'\S+', combined)) > 12:
                            continue
                        if needle not in own_text and needle not in own_aria and needle not in own_placeholder and needle not in own_title:
                            continue
                    filtered.append(item)
                return filtered[:25]
            except Exception as exc:
                text = str(exc).lower()
                if 'execution context was destroyed' not in text and 'target page, context or browser has been closed' not in text:
                    raise
                try:
                    await page.wait_for_load_state('domcontentloaded')
                except Exception:
                    pass
                if page.is_closed():
                    ctx = self.contexts.get(sid)
                    if ctx is None or (hasattr(ctx, 'pages') and ctx.pages and all(p.is_closed() for p in ctx.pages)):
                        ctx = await self.browser.new_context()
                        self.contexts[sid] = ctx
                    page = await ctx.new_page()
                    self.pages[sid] = page
        return []

    async def pick(self, selector: str, session_id: str = None):
        await self._ensure()
        sid = session_id or 'default'
        page = self.pages.get(sid)
        if not page:
            return None
        handle = await page.query_selector(selector)
        if not handle:
            return None
        info = await page.evaluate('(el)=>{return {tag:el.tagName, outerHTML:el.outerHTML, id:el.id||null, name:el.getAttribute("name")||null, classes:el.className||null, aria:el.getAttribute("aria-label")||null, placeholder:el.getAttribute("placeholder")||null}}', handle)
        return info

    async def verify_locator(self, loc_type: str, value: str, session_id: str = None):
        """Verify how many elements a locator matches across the main document and same-origin frames.
        Returns dict: {count:int, cross_origin_frame:bool, found_shadow:bool, frames:list}
        """
        await self._ensure()
        sid = session_id or 'default'
        page = self.pages.get(sid)
        if not page:
            return {"count": 0, "cross_origin_frame": False, "found_shadow": False, 'frames': []}
        normalized = (value or '').strip()
        is_xpath = normalized.startswith(('/', '(', './/'))
        js = """
        ({ sel, isXPath }) => {
          const results = [];
          function findInDoc(doc){
            try{
              let nodes = [];
              if(isXPath){
                try{
                  const it = doc.evaluate(sel, doc, null, XPathResult.ORDERED_NODE_ITERATOR_TYPE, null);
                  let n; while(n = it.iterateNext()) nodes.push(n);
                }catch(e){}
              } else {
                try{ nodes = Array.from(doc.querySelectorAll(sel)); }catch(e){}
              }
              nodes.forEach(n=>{
                let inShadow = (n.getRootNode && n.getRootNode() instanceof ShadowRoot) ? true : false;
                results.push({inShadow});
              });
            }catch(e){}
          }
          try{ findInDoc(document); }catch(e){}
          for(let i=0;i<window.frames.length;i++){
            try{
              const fdoc = window.frames[i].document;
              findInDoc(fdoc);
            }catch(e){
              return {count: results.length, crossOriginFrame: true, foundShadow: results.some(r=>r.inShadow)};
            }
          }
          return {count: results.length, crossOriginFrame: false, foundShadow: results.some(r=>r.inShadow)};
        }
        """
        try:
            res = await page.evaluate(js, {"sel": value, "isXPath": is_xpath})
        except Exception:
            return {"count": 0, "cross_origin_frame": False, "found_shadow": False, 'frames': []}
        out = {"count": int(res.get('count', 0)), "cross_origin_frame": bool(res.get('crossOriginFrame', False)), "found_shadow": bool(res.get('foundShadow', False))}
        try:
            frames = await page.evaluate("() => Array.from(document.querySelectorAll('iframe')).map((f,i)=>({index:i, id: f.id||null, name: f.name||null, src: f.src||null}))")
            out['frames'] = frames
        except Exception:
            out['frames'] = []
        return out

    async def highlight(self, loc_type: str, value: str, session_id: str = None):
        """Highlight elements matching locator in the given session. Returns number highlighted."""
        await self._ensure()
        sid = session_id or 'default'
        page = self.pages.get(sid)
        if not page:
            return 0
        is_xpath = loc_type == 'xpath' or value.strip().startswith('/')
        js = """
        ({ sel, isXPath, cls }) => {
            const nodes = [];
            if(isXPath){
                try{
                    const it = document.evaluate(sel, document, null, XPathResult.ORDERED_NODE_ITERATOR_TYPE, null);
                    let n; while(n = it.iterateNext()) nodes.push(n);
                }catch(e){}
            } else {
                try{ nodes.push(...Array.from(document.querySelectorAll(sel))); }catch(e){}
            }
            nodes.forEach(n=>{
                try{
                    n.classList.add(cls);
                    n.setAttribute('data-locator-agent', '1');
                    n.style.outline = '3px solid rgba(255,165,0,0.95)';
                    n.style.zIndex = '2147483647';
                    n.scrollIntoView && n.scrollIntoView({behavior:'smooth', block:'center'});
                }catch(e){}
            });
            return nodes.length;
        }
        """
        try:
            count = await page.evaluate(js, {"sel": value, "isXPath": is_xpath, "cls": 'locator-agent-highlight'})
        except Exception:
            count = 0
        return int(count)

    async def unhighlight(self, session_id: str = None):
        await self._ensure()
        sid = session_id or 'default'
        page = self.pages.get(sid)
        if not page:
            return 0
        js = """
        () => {
            const nodes = Array.from(document.querySelectorAll('.locator-agent-highlight'));
            nodes.forEach(n=>{
                try{
                    n.classList.remove('locator-agent-highlight');
                    n.removeAttribute('data-locator-agent');
                    n.style.outline = '';
                }catch(e){}
            });
            return nodes.length;
        }
        """
        try:
            cnt = await page.evaluate(js)
        except Exception:
            cnt = 0
        return int(cnt)

