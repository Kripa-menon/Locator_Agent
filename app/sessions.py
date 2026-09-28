import json
import os
import uuid
from datetime import datetime


class SessionStore:
    def __init__(self, path=None):
        self.path = path or os.path.join(os.path.dirname(__file__), '..', 'sessions.json')
        self.path = os.path.abspath(self.path)
        self.sessions = {}
        self._load()

    def _load(self):
        try:
            if os.path.exists(self.path):
                with open(self.path, 'r', encoding='utf-8') as f:
                    self.sessions = json.load(f)
            else:
                self.sessions = {}
        except Exception:
            self.sessions = {}

    def _save(self):
        try:
            os.makedirs(os.path.dirname(self.path), exist_ok=True)
            with open(self.path, 'w', encoding='utf-8') as f:
                json.dump(self.sessions, f, indent=2)
        except Exception:
            pass

    def create(self, name=None):
        sid = str(uuid.uuid4())
        meta = {
            'id': sid,
            'name': name or sid,
            'created_at': datetime.utcnow().isoformat() + 'Z',
            'last_url': None,
            'storage': None,
        }
        self.sessions[sid] = meta
        self._save()
        return meta

    def list(self):
        return list(self.sessions.values())

    def get(self, sid):
        return self.sessions.get(sid)

    def update(self, sid, **kwargs):
        if sid in self.sessions:
            self.sessions[sid].update(kwargs)
            self._save()
            return self.sessions[sid]
        return None

    def delete(self, sid):
        if sid in self.sessions:
            del self.sessions[sid]
            self._save()
            return True
        return False
