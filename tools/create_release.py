#!/usr/bin/env python3
import os
import sys
import json
import argparse
from urllib import request, parse, error


def api_request(url, method='GET', data=None, headers=None):
    if headers is None:
        headers = {}
    req = request.Request(url, data=data, headers=headers, method=method)
    try:
        with request.urlopen(req) as resp:
            return resp.getcode(), resp.read().decode('utf-8')
    except error.HTTPError as e:
        return e.code, e.read().decode('utf-8')


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--repo', required=True)
    p.add_argument('--tag', required=True)
    p.add_argument('--name', required=True)
    p.add_argument('--file', required=True)
    p.add_argument('--notes', default='Auto release')
    args = p.parse_args()

    token = os.environ.get('GITHUB_TOKEN')
    if not token:
        print('GITHUB_TOKEN not set in environment', file=sys.stderr)
        sys.exit(2)

    api_url = f'https://api.github.com/repos/{args.repo}/releases'
    payload = {
        'tag_name': args.tag,
        'name': args.name,
        'body': args.notes,
        'draft': False,
        'prerelease': False,
    }
    data = json.dumps(payload).encode('utf-8')
    headers = {
        'Authorization': f'token {token}',
        'Accept': 'application/vnd.github+json',
        'Content-Type': 'application/json',
        'User-Agent': 'Locator-Agent-Uploader'
    }
    code, text = api_request(api_url, method='POST', data=data, headers=headers)
    if code not in (200,201):
        print('Failed to create release', code, text, file=sys.stderr)
        sys.exit(3)
    resp = json.loads(text)
    upload_url = resp.get('upload_url')
    if not upload_url:
        print('No upload_url in response', file=sys.stderr)
        sys.exit(4)
    upload_base = upload_url.split('{')[0]

    fname = os.path.abspath(args.file)
    if not os.path.exists(fname):
        print('File not found: ' + fname, file=sys.stderr)
        sys.exit(5)

    upload_full = upload_base + '?name=' + parse.quote(os.path.basename(fname))
    with open(fname, 'rb') as f:
        bin_data = f.read()

    headers2 = {
        'Authorization': f'token {token}',
        'Content-Type': 'application/zip',
        'User-Agent': 'Locator-Agent-Uploader'
    }
    code2, text2 = api_request(upload_full, method='POST', data=bin_data, headers=headers2)
    if code2 not in (200,201):
        print('Failed to upload asset', code2, text2, file=sys.stderr)
        sys.exit(6)
    print('Release created and asset uploaded successfully')


if __name__ == '__main__':
    main()
