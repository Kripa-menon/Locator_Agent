import pytest

from app.browser import BrowserController


@pytest.mark.asyncio
async def test_open_recreates_closed_default_page():
    browser = BrowserController()
    await browser.start()

    page = browser.pages['default']
    await page.close()
    browser.pages['default'] = page

    await browser.open('https://example.com', session_id='default')

    assert 'default' in browser.pages
    assert browser.pages['default'] is not None
    assert not browser.pages['default'].is_closed()

    await browser.close()


@pytest.mark.asyncio
async def test_find_by_description_matches_demoqa_label_and_placeholder():
    browser = BrowserController()
    await browser.start()

    class FakePage:
        async def evaluate(self, script, arg=None):
            if not arg:
                return []
            if 'Full Name'.lower() in str(arg).lower():
                return [{
                    'tag': 'INPUT',
                    'outerHTML': '<input id="userName" placeholder="Full Name" />',
                    'id': 'userName',
                    'name': None,
                    'classes': None,
                    'aria': None,
                    'placeholder': 'Full Name',
                    'label': None,
                    'text': None,
                    'title': None,
                }]
            return []

    browser.pages['demoqa-label'] = FakePage()
    results = await browser.find_by_description('Full Name', session_id='demoqa-label')

    assert results, 'Expected the text-box label or placeholder to match "Full Name"'
    assert any(
        'Full Name'.lower() in str(item.get('placeholder') or '').lower()
        or 'Full Name'.lower() in str(item.get('aria') or '').lower()
        or 'Full Name'.lower() in str(item.get('text') or '').lower()
        for item in results
    )

    await browser.close()


@pytest.mark.asyncio
async def test_find_by_description_matches_adjacent_text_for_checkbox():
    browser = BrowserController()
    await browser.start()

    class FakePage:
        async def evaluate(self, script, arg=None):
            if not arg:
                return []
            needle = str(arg).lower()
            if 'checkbox 2' in needle:
                if 'previousSibling' in script and 'nextSibling' in script:
                    return [{
                        'tag': 'INPUT',
                        'outerHTML': "<input type='checkbox' checked> checkbox 2",
                        'id': None,
                        'name': None,
                        'classes': None,
                        'aria': None,
                        'placeholder': None,
                        'label': 'checkbox 2',
                        'text': 'checkbox 2',
                        'title': None,
                    }]
            return []

    browser.pages['checkbox-adjacent'] = FakePage()
    results = await browser.find_by_description('checkbox 2', session_id='checkbox-adjacent')

    assert results, 'Expected adjacent text like "checkbox 2" to be recognized as a label.'
    assert any('checkbox 2' in str(item.get('label') or '').lower() or 'checkbox 2' in str(item.get('text') or '').lower() for item in results)

    await browser.close()


@pytest.mark.asyncio
async def test_find_by_description_ignores_first_name_from_neighboring_input_when_matching_email():
    browser = BrowserController()
    await browser.start()

    class FakePage:
        def is_closed(self):
            return False

        async def evaluate(self, script, arg=None):
            if not arg:
                return []
            needle = str(arg).lower()
            if 'first name' in needle:
                return [
                    {
                        'tag': 'INPUT',
                        'outerHTML': '<input id="userEmail" name="userEmail" type="email" />',
                        'id': 'userEmail',
                        'name': 'userEmail',
                        'classes': '',
                        'aria': None,
                        'placeholder': 'Email',
                        'label': 'Email',
                        'text': None,
                        'title': None,
                    },
                    {
                        'tag': 'INPUT',
                        'outerHTML': '<input id="firstName" name="firstName" type="text" />',
                        'id': 'firstName',
                        'name': 'firstName',
                        'classes': '',
                        'aria': None,
                        'placeholder': 'First Name',
                        'label': 'First Name',
                        'text': None,
                        'title': None,
                    },
                ]
            return []

    browser.pages['default'] = FakePage()
    results = await browser.find_by_description('first name', session_id='default')

    assert results, 'Expected the first-name input to be returned.'
    assert any(item.get('id') == 'firstName' for item in results)
    assert not any(item.get('id') == 'userEmail' for item in results)

    await browser.close()


@pytest.mark.asyncio
async def test_verify_locator_handles_positional_xpath_value():
    browser = BrowserController()
    await browser.start()
    page = browser.pages['default']
    await page.set_content("<html><body><input type='checkbox'> checkbox 1<br><input type='checkbox' checked> checkbox 2</body></html>")

    result = await browser.verify_locator('xpath', '(//input)[1]', session_id='default')

    assert result['count'] >= 1, 'Expected a positional XPath like (//input)[1] to be recognized as XPath and match the checkbox.'

    await browser.close()


@pytest.mark.asyncio
async def test_find_by_description_prefers_checkbox_over_generic_fork_banner():
    browser = BrowserController()
    await browser.start()

    class FakePage:
        def is_closed(self):
            return False

        async def evaluate(self, script, arg=None):
            if not arg:
                return []
            needle = str(arg).lower()
            if 'checkbox 2' in needle:
                return [
                    {
                        'tag': 'A',
                        'outerHTML': '<a href="https://github.com/tourdedave/the-internet"><img alt="Fork me on GitHub" /></a>',
                        'id': None,
                        'name': None,
                        'classes': None,
                        'aria': 'Fork me on GitHub',
                        'placeholder': None,
                        'label': None,
                        'text': None,
                        'title': None,
                    },
                    {
                        'tag': 'INPUT',
                        'outerHTML': "<input type='checkbox' checked />",
                        'id': None,
                        'name': None,
                        'classes': None,
                        'aria': None,
                        'placeholder': None,
                        'label': 'checkbox 2',
                        'text': 'checkbox 2',
                        'title': None,
                    },
                ]
            return []

    browser.pages['default'] = FakePage()
    results = await browser.find_by_description('checkbox 2', session_id='default')

    assert results, 'Expected the checkbox description to identify at least one element.'
    assert any(item.get('tag') == 'INPUT' and 'checkbox 2' in str(item.get('label') or item.get('text') or '').lower() for item in results)
    assert not any(item.get('tag') == 'A' for item in results)

    await browser.close()


@pytest.mark.asyncio
async def test_find_by_description_ignores_button_when_username_is_a_neighboring_label():
    browser = BrowserController()
    await browser.start()

    class FakePage:
        def is_closed(self):
            return False

        async def evaluate(self, script, arg=None):
            if not arg:
                return []
            needle = str(arg).lower()
            if 'username' in needle:
                return [
                    {
                        'tag': 'BUTTON',
                        'outerHTML': '<button type="submit">Login</button>',
                        'id': None,
                        'name': None,
                        'classes': None,
                        'aria': None,
                        'placeholder': None,
                        'label': 'username Login',
                        'text': 'Login',
                        'title': None,
                    },
                    {
                        'tag': 'INPUT',
                        'outerHTML': '<input type="text" placeholder="Username" />',
                        'id': None,
                        'name': None,
                        'classes': None,
                        'aria': None,
                        'placeholder': 'Username',
                        'label': 'Username',
                        'text': None,
                        'title': None,
                    },
                ]
            return []

    browser.pages['default'] = FakePage()
    results = await browser.find_by_description('username', session_id='default')

    assert results, 'Expected the username field to match.'
    assert any(item.get('tag') == 'INPUT' and 'username' in str(item.get('placeholder') or item.get('label') or '').lower() for item in results)
    assert not any(item.get('tag') == 'BUTTON' for item in results)

    await browser.close()


@pytest.mark.asyncio
async def test_find_by_description_accepts_edit_action_link_for_button_query():
    browser = BrowserController()
    await browser.start()

    class FakePage:
        def is_closed(self):
            return False

        async def evaluate(self, script, arg=None):
            if not arg:
                return []
            needle = str(arg).lower()
            if 'edit button' in needle:
                return [
                    {
                        'tag': 'A',
                        'outerHTML': '<a href="#edit">edit</a>',
                        'id': None,
                        'name': None,
                        'classes': None,
                        'aria': None,
                        'placeholder': None,
                        'label': 'edit',
                        'text': 'edit',
                        'title': None,
                    },
                    {
                        'tag': 'A',
                        'outerHTML': '<a href="#delete">delete</a>',
                        'id': None,
                        'name': None,
                        'classes': None,
                        'aria': None,
                        'placeholder': None,
                        'label': 'delete',
                        'text': 'delete',
                        'title': None,
                    },
                ]
            return []

    browser.pages['default'] = FakePage()
    results = await browser.find_by_description('edit button', session_id='default')

    assert results, 'Expected the edit action link to match the button-like query.'
    assert any(item.get('tag') == 'A' and 'edit' in str(item.get('text') or item.get('label') or '').lower() for item in results)
    assert not any(item.get('tag') == 'A' and 'delete' in str(item.get('text') or item.get('label') or '').lower() for item in results)

    await browser.close()


@pytest.mark.asyncio
async def test_find_by_description_requires_birth_tokens_not_shared_with_date_picker():
    browser = BrowserController()
    await browser.start()

    class FakePage:
        def is_closed(self):
            return False

        async def evaluate(self, script, arg=None):
            if not arg:
                return []
            needle = str(arg).lower()
            if 'date of birth' in needle:
                return [
                    {
                        'tag': 'A',
                        'outerHTML': '<a href="/date-picker">Date Picker</a>',
                        'id': None,
                        'name': None,
                        'classes': None,
                        'aria': None,
                        'placeholder': None,
                        'label': 'Date Picker',
                        'text': 'Date Picker',
                        'title': None,
                    },
                    {
                        'tag': 'INPUT',
                        'outerHTML': '<input id="dateOfBirthInput" />',
                        'id': 'dateOfBirthInput',
                        'name': None,
                        'classes': None,
                        'aria': None,
                        'placeholder': None,
                        'label': 'Date of Birth',
                        'text': 'Date of Birth',
                        'title': None,
                    },
                ]
            return []

    browser.pages['default'] = FakePage()
    results = await browser.find_by_description('Date of Birth', session_id='default')

    assert results, 'Expected the date-of-birth input to match.'
    assert any(item.get('tag') == 'INPUT' and 'dateofbirth' in str(item.get('label') or item.get('text') or item.get('id') or '').lower().replace(' ', '') for item in results)
    assert not any(item.get('tag') == 'A' and 'date picker' in str(item.get('label') or item.get('text') or '').lower() for item in results)

    await browser.close()


@pytest.mark.asyncio
async def test_find_by_description_ignores_generic_header_link_containing_page_text():
    browser = BrowserController()
    await browser.start()

    class FakePage:
        def is_closed(self):
            return False

        async def evaluate(self, script, arg=None):
            if not arg:
                return []
            needle = str(arg).lower()
            if 'username' in needle:
                return [
                    {
                        'tag': 'A',
                        'outerHTML': '<a href="https://github.com/tourdedave/the-internet"><img alt="Fork me on GitHub" /></a>',
                        'id': None,
                        'name': None,
                        'classes': None,
                        'aria': 'Fork me on GitHub',
                        'placeholder': None,
                        'label': 'Login Page This is where you can log into the secure area. Enter tomsmith for the username and SuperSecretPassword! for the password. If the information is wrong you should see error messages. Username Password Login',
                        'text': 'Login Page This is where you can log into the secure area. Enter tomsmith for the username and SuperSecretPassword! for the password. If the information is wrong you should see error messages. Username Password Login',
                        'title': None,
                    },
                    {
                        'tag': 'INPUT',
                        'outerHTML': '<input type="text" name="username" id="username" />',
                        'id': 'username',
                        'name': 'username',
                        'classes': None,
                        'aria': None,
                        'placeholder': None,
                        'label': 'Username',
                        'text': 'Username',
                        'title': None,
                    },
                ]
            return []

    browser.pages['default'] = FakePage()
    results = await browser.find_by_description('username', session_id='default')

    assert results, 'Expected the username input to be returned.'
    assert any(item.get('tag') == 'INPUT' for item in results)
    assert not any(item.get('tag') == 'A' for item in results)

    await browser.close()
