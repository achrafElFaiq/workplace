"""
blocked.py — manage blocked senders stored in data/blocked_senders.json
"""
import json
import os
from datetime import datetime

BLOCKED_FILE = os.path.join(os.path.dirname(__file__), "data", "blocked_senders.json")


def _load() -> list[dict]:
    if os.path.exists(BLOCKED_FILE):
        with open(BLOCKED_FILE) as f:
            return json.load(f)
    return []


def _save(entries: list[dict]):
    os.makedirs(os.path.dirname(BLOCKED_FILE), exist_ok=True)
    with open(BLOCKED_FILE, "w") as f:
        json.dump(entries, f, indent=2)


def get_blocked_senders() -> set[str]:
    return {e["address"].lower() for e in _load()}


def add_blocked_sender(address: str):
    address = address.lower().strip()
    entries = _load()
    if not any(e["address"] == address for e in entries):
        entries.append({"address": address, "blocked_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")})
        _save(entries)


def remove_blocked_sender(address: str):
    address = address.lower().strip()
    entries = [e for e in _load() if e["address"] != address]
    _save(entries)


def list_blocked() -> list[dict]:
    return sorted(_load(), key=lambda e: e.get("blocked_at", ""), reverse=True)
