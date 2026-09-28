from fastapi import FastAPI, Request, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse
from .browser import BrowserController
from .locator import LocatorService
from .codegen import CodeGenerator
import os

app = FastAPI()

app.mount("/static", StaticFiles(directory=os.path.join(os.path.dirname(__file__), '..', 'static')), name="static")

browser = BrowserController()
from .sessions import SessionStore
store = SessionStore()

locator = LocatorService()
codegen = CodeGenerator()


@app.get("/")
async def index():
    html_path = os.path.join(os.path.dirname(__file__), "..", "static", "index.html")
    with open(html_path, "r", encoding="utf-8") as f:
        return HTMLResponse(f.read())


@app.post("/open")
async def open_url(req: Request):
    data = await req.json()
    url = data.get("url")
    if not url:
        raise HTTPException(status_code=400, detail="Missing url")
    session = data.get('session')
    try:
        await browser.start()
        await browser.open(url, session_id=session)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    return JSONResponse({"status": "opened"})


@app.post('/start')
async def start_browser():
    try:
        await browser.start()
        return JSONResponse({'status': 'started'})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post('/sessions')
async def create_session(req: Request):
    data = await req.json()
    name = data.get('name')
    s = store.create(name)
    return JSONResponse(s)


@app.get('/sessions')
async def list_sessions():
    return JSONResponse(store.list())


@app.get('/sessions/{sid}')
async def get_session(sid: str):
    s = store.get(sid)
    if not s:
        raise HTTPException(status_code=404, detail='not found')
    return JSONResponse(s)


@app.post('/sessions/{sid}/activate')
async def activate_session(sid: str):
    s = store.get(sid)
    if not s:
        raise HTTPException(status_code=404, detail='not found')
    # create a new browser context for this session id
    await browser._ensure()
    ctx = await browser.browser.new_context()
    page = await ctx.new_page()
    browser.contexts[sid] = ctx
    browser.pages[sid] = page
    store.update(sid, last_url=None)
    return JSONResponse({'status': 'activated', 'id': sid})


@app.post('/sessions/{sid}/close')
async def close_session(sid: str):
    if sid in browser.pages:
        try:
            await browser.pages[sid].close()
        except Exception:
            pass
        del browser.pages[sid]
    if sid in browser.contexts:
        try:
            await browser.contexts[sid].close()
        except Exception:
            pass
        del browser.contexts[sid]
    store.delete(sid)
    return JSONResponse({'status': 'closed', 'id': sid})


@app.post('/stop')
async def stop_browser():
    try:
        await browser.close()
        return JSONResponse({'status': 'stopped'})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get('/status')
async def browser_status():
    st = await browser.status()
    return JSONResponse(st)


@app.post("/continue")
async def continue_after_login():
    return JSONResponse({"status": "ready"})


@app.post("/describe")
async def describe(req: Request):
    data = await req.json()
    description = data.get("description")
    if not description:
        raise HTTPException(status_code=400, detail="Missing description")
    session = data.get('session')
    elements = await browser.find_by_description(description, session_id=session)
    if not elements:
        return JSONResponse({"matches": []})
    results = []
    for el in elements:
        ranked = locator.rank_element(el)
        # verify candidates
        for c in [ranked['best']] + ranked.get('alternatives', []):
            if not c:
                continue
            loc_type = c['type']
            val = c['value']
            # for xpath provide string starting with // or /
            if loc_type == 'xpath' and not val.startswith('/'):
                val = '//' + val
            ver = await browser.verify_locator(loc_type, val, session_id=session)
            c['match_count'] = ver.get('count', 0)
            c['cross_origin_frame'] = ver.get('cross_origin_frame', False)
            c['found_shadow'] = ver.get('found_shadow', False)
            # include frame hints if available
            c['frames'] = ver.get('frames', [])
        # choose best that matches exactly 1
        best = None
        if ranked['best'] and ranked['best'].get('match_count') == 1:
            best = ranked['best']
        else:
            for alt in ranked.get('alternatives', []):
                if alt.get('match_count') == 1:
                    best = alt
                    break
        ranked['chosen_best'] = best or ranked['best']
        # if chosen_best indicates frames, pick a likely frame hint
        frame_hint = None
        if ranked['chosen_best'] and ranked['chosen_best'].get('frames'):
            # pick first non-empty src or named frame
            for f in ranked['chosen_best']['frames']:
                if f.get('name') or f.get('id') or f.get('src'):
                    frame_hint = f
                    break
        code = codegen.generate(ranked['chosen_best'], frame_hint)
        results.append({"ranked": ranked, "code": code})
    return JSONResponse({"matches": results})


@app.post('/highlight')
async def highlight(req: Request):
    data = await req.json()
    loc_type = data.get('type')
    value = data.get('value')
    session = data.get('session')
    if not loc_type or not value:
        raise HTTPException(status_code=400, detail='missing')
    count = await browser.highlight(loc_type, value, session_id=session)
    return JSONResponse({'highlighted': count})


@app.post('/unhighlight')
async def unhighlight(req: Request):
    data = await req.json()
    session = data.get('session')
    cnt = await browser.unhighlight(session_id=session)
    return JSONResponse({'unhighlighted': cnt})


@app.post("/pick")
async def pick_element(req: Request):
    data = await req.json()
    selector = data.get("selector")
    session = data.get('session')
    if not selector:
        raise HTTPException(status_code=400, detail="Missing selector")
    el = await browser.pick(selector, session_id=session)
    ranked = locator.rank_element(el)
    code = codegen.generate(ranked['best'], ranked.get('frame'))
    return JSONResponse({"ranked": ranked, "code": code})



@app.on_event("shutdown")
async def shutdown_event():
    try:
        await browser.close()
    except Exception:
        pass
