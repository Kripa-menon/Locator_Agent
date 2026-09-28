import asyncio
from playwright.async_api import async_playwright
import re


class BrowserController:
    def __init__(self):
        self.playwright = None
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
            if self.playwright:
                try:
                    await self.playwright.stop()
                except Exception:
                    pass
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
            self.playwright = await async_playwright().start()
        if not self.browser:
            self.browser = await self.playwright.chromium.launch(headless=False)
        # ensure default context/page
        if 'default' not in self.pages:
            ctx = await self.browser.new_context()
            pg = await ctx.new_page()
            self.contexts['default'] = ctx
            self.pages['default'] = pg

    async def open(self, url: str, session_id: str = None):
        await self._ensure()
        sid = session_id or 'default'
        page = self.pages.get(sid)
        if not page:
            ctx = await self.browser.new_context()
            page = await ctx.new_page()
            self.contexts[sid] = ctx
            self.pages[sid] = page
        return await page.goto(url)

    async def find_by_description(self, description: str, session_id: str = None):
        await self._ensure()
        sid = session_id or 'default'
        page = self.pages.get(sid)
        if not page:
            return []
        js = f"""
        (function(){{
          const desc = `{description}`.toLowerCase();
          const results = [];
          document.querySelectorAll('*').forEach(el => {{
            try{{
              const text = (el.innerText||el.value||'').toLowerCase();
              const aria = (el.getAttribute('aria-label')||'').toLowerCase();
              if(text.includes(desc) || aria.includes(desc)){{
                results.push(el);
              }}
            }}catch(e){{}}
          }});
          return results.map(e=>({{
            tag: e.tagName,
            outerHTML: e.outerHTML,
            id: e.id || null,
            name: e.getAttribute('name') || null,
            classes: e.className || null,
            aria: e.getAttribute('aria-label') || null,
            placeholder: e.getAttribute('placeholder') || null,
          }}));
        }})();
        """
        return await page.evaluate(js)

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
        is_xpath = value.strip().startswith('/')
        js = """
        (sel, isXPath) => {
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
            res = await page.evaluate(js, value, is_xpath)
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
                (sel, isXPath, cls) => {
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
                        count = await page.evaluate(js, value, is_xpath, 'locator-agent-highlight')
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

