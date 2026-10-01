# Locator Finder Agent

Runs locally. Uses FastAPI + Playwright to open a visible browser so you can log in to protected sites.

## Prerequisites

Before running the project, make sure the following are installed:

- Python 3.10 or newer
- Git
- PowerShell, Command Prompt, or Git Bash on Windows

## Windows setup from scratch

### PowerShell / Command Prompt

```powershell
git clone https://github.com/Kripa-menon/Locator_Agent.git
cd Locator_Agent
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
python -m playwright install chromium
uvicorn app.main:app --reload
```

Open: http://127.0.0.1:8000

### Git Bash

```bash
git clone https://github.com/Kripa-menon/Locator_Agent.git
cd Locator_Agent
python -m venv .venv
source .venv/Scripts/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
python -m playwright install chromium
uvicorn app.main:app --reload
```

### If PowerShell blocks activation

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

### If Playwright browser install fails

```powershell
python -m playwright install --with-deps chromium
```

## Setup

1. Create a venv and activate it

```bash
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
python -m playwright install chromium
```

Run

```bash
uvicorn app.main:app --reload
```

Install linters and enable pre-commit hooks:

```bash
pip install -r requirements.txt
pre-commit install
pre-commit run --all-files
```

Open http://127.0.0.1:8000 and use the UI.

Notes

- The app opens a visible Chromium; log in manually then click Continue.
- This is a minimal prototype. Locator ranking, verification, and LLM integration are basic and can be improved.
- If the element is inside an iframe, the tool will detect cross-origin frames and flag them; you'll need to switch to the frame in your test code.
- If the element is inside shadow DOM, the tool will flag it and provide a JS-based approach may be required.

Testing on a public sample

1. Run the app:

```bash
uvicorn app.main:app --reload
```

2. Open http://127.0.0.1:8000 and enter `https://example.com` as URL, click Open.
3. Use the description field to search for elements (e.g., "More information").

For a real login page (e.g., https://github.com/login), open the URL, log in manually in the opened browser, click Continue, then describe or pick elements.

Publishing Releases

When you push a tag to the repository, GitHub Actions will build a zip and create a release automatically.

Steps to publish a release locally (optional):

1. Create a tag and push it:

```bash
git tag v0.1.0
git push origin --tags
```

2. After the tag is pushed, check the Actions tab on GitHub to monitor the `Publish Release on Tag` workflow.

Notes

- The workflow uses the repository `GITHUB_TOKEN` secret automatically; you do not need to add a personal token for basic releases. If you need to upload additional artifacts or use a different account, set the `GITHUB_TOKEN` or a personal access token in the repo secrets.
- The workflow zips the repository root and excludes large folders like `.venv` and `node_modules`.
