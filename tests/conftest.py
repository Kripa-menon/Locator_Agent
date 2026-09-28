import sys
import types

# Provide a minimal fake for playwright.async_api so tests don't require Playwright installed.
playwright_mod = types.ModuleType('playwright')
async_api = types.ModuleType('playwright.async_api')

async def async_playwright():
    # stub async function; tests should not call it.
    async def _inner():
        return None
    return _inner

async_api.async_playwright = async_playwright

sys.modules['playwright'] = playwright_mod
sys.modules['playwright.async_api'] = async_api
