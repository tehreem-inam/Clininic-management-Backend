"""Lightweight auth cache service used by auth dependencies.

Provides simple thread-safe in-memory caches for decoded JWT payloads and
resolved user contexts. Kept intentionally small and dependency-free so it
can be imported by `app.auth.dependencies` without circular imports.

This module's functions are safe-to-call: cache failures are swallowed so
that auth behavior falls back to the original decode+DB lookup.
"""
from __future__ import annotations

from collections import OrderedDict
from threading import Lock
from typing import Optional, Tuple, Dict, Any
import time

# Optional runtime configuration: try to import settings but don't require it
try:
    from app.settings import settings
    _USE_SETTINGS = True
except Exception:
    settings = None
    _USE_SETTINGS = False

# Token cache: token -> (payload_dict, exp_ts)
# Token cache: token -> (payload_dict, exp_ts)
_TOKEN_CACHE: "OrderedDict[str, Tuple[Dict[str, Any], Optional[float]]]" = OrderedDict()
_TOKEN_CACHE_LOCK = Lock()
# Apply configured max if available
try:
    _TOKEN_CACHE_MAX = int(getattr(settings, "auth_cache_token_max", 1024)) if _USE_SETTINGS else 1024
except Exception:
    _TOKEN_CACHE_MAX = 1024

# User context cache: user_id -> (ctx_dict, expiry_ts)
_USER_CACHE: "OrderedDict[int, Tuple[Dict[str, Any], float]]" = OrderedDict()
_USER_CACHE_LOCK = Lock()
# Apply configured user cache size and TTL if available
try:
    _USER_CACHE_MAX = int(getattr(settings, "auth_cache_user_max", 4096)) if _USE_SETTINGS else 4096
    _USER_CACHE_TTL = float(getattr(settings, "auth_cache_user_ttl", 30.0)) if _USE_SETTINGS else 30.0
except Exception:
    _USER_CACHE_MAX = 4096
    _USER_CACHE_TTL = 30.0

# Counters for instrumentation (best-effort)
_HITS = {"token": 0, "user": 0}
_MISSES = {"token": 0, "user": 0}


def get_cached_token(token: str) -> Optional[Dict[str, Any]]:
    """Return payload dict if token is cached and not expired, else None."""
    try:
        with _TOKEN_CACHE_LOCK:
            item = _TOKEN_CACHE.get(token)
            if not item:
                _MISSES["token"] += 1
                return None
            payload, exp_ts = item
            if exp_ts is not None and exp_ts < time.time():
                # expired
                try:
                    del _TOKEN_CACHE[token]
                except KeyError:
                    pass
                _MISSES["token"] += 1
                return None
            # update LRU
            _TOKEN_CACHE.move_to_end(token)
            _HITS["token"] += 1
            return payload
    except Exception:
        # Cache is best-effort. Do not raise from here.
        return None


def set_cached_token(token: str, payload: Dict[str, Any]) -> None:
    """Store decoded token payload; exp field is used for expiry if present."""
    try:
        exp = payload.get("exp")
        exp_ts = float(exp) if exp is not None else None
        with _TOKEN_CACHE_LOCK:
            _TOKEN_CACHE[token] = (payload, exp_ts)
            _TOKEN_CACHE.move_to_end(token)
            while len(_TOKEN_CACHE) > _TOKEN_CACHE_MAX:
                _TOKEN_CACHE.popitem(last=False)
    except Exception:
        # best-effort, swallow errors
        return


def get_cached_user(user_id: int) -> Optional[Dict[str, Any]]:
    """Return cached user context dict if not expired, else None."""
    try:
        with _USER_CACHE_LOCK:
            item = _USER_CACHE.get(user_id)
            if not item:
                _MISSES["user"] += 1
                return None
            data, exp_ts = item
            if exp_ts < time.time():
                try:
                    del _USER_CACHE[user_id]
                except KeyError:
                    pass
                _MISSES["user"] += 1
                return None
            _USER_CACHE.move_to_end(user_id)
            _HITS["user"] += 1
            return data
    except Exception:
        return None


def set_cached_user(user_id: int, data: Dict[str, Any]) -> None:
    """Cache a lightweight user context dict for a short TTL."""
    try:
        exp_ts = time.time() + _USER_CACHE_TTL
        with _USER_CACHE_LOCK:
            _USER_CACHE[user_id] = (data, exp_ts)
            _USER_CACHE.move_to_end(user_id)
            while len(_USER_CACHE) > _USER_CACHE_MAX:
                _USER_CACHE.popitem(last=False)
    except Exception:
        return


def delete_cached_user(user_id: int) -> None:
    try:
        with _USER_CACHE_LOCK:
            if user_id in _USER_CACHE:
                del _USER_CACHE[user_id]
    except Exception:
        return


def delete_cached_token(token: str) -> None:
    try:
        with _TOKEN_CACHE_LOCK:
            if token in _TOKEN_CACHE:
                del _TOKEN_CACHE[token]
    except Exception:
        return


def get_metrics() -> Dict[str, Dict[str, int]]:
    """Return simple hit/miss metrics for monitoring (best-effort)."""
    return {"hits": dict(_HITS), "misses": dict(_MISSES)}


__all__ = [
    "get_cached_token",
    "set_cached_token",
    "get_cached_user",
    "set_cached_user",
]
