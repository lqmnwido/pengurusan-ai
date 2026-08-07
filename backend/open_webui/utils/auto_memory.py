from __future__ import annotations

import logging
import re
import string

from fastapi import Request

from open_webui.models.memories import Memories
from open_webui.routers.memories import create_memory_entry
from open_webui.utils.access_control import has_permission
from open_webui.utils.misc import get_last_user_message

log = logging.getLogger(__name__)

MAX_AUTO_MEMORIES_PER_MESSAGE = 3
MAX_MEMORY_LENGTH = 500

_SENSITIVE_RE = re.compile(
    r'\b(password|passcode|secret|token|api[_ -]?key|private key|seed phrase|credit card|cvv|otp|2fa)\b',
    re.I,
)
_OPT_OUT_RE = re.compile(r"\b(don't|do not|dont|never)\s+(remember|save|store)\b", re.I)
_EXPLICIT_MEMORY_RE = re.compile(
    r'\b(?:please\s+)?(?:remember|save|store|keep in memory|for future reference)\s+(?:that\s+)?(.+)',
    re.I | re.S,
)
_FACT_RE = re.compile(
    r'\b(?:'
    r'my\s+(?:name|email|role|job|company|organization|museum|project|website|domain|server|stack|'
    r'preference|preferred language|timezone|location)\s+(?:is|are)|'
    r'i\s+(?:am|prefer|like|use|work at|work for|run|manage|own)|'
    r'we\s+(?:use|run|manage|own|prefer)|'
    r'our\s+(?:project|system|website|museum|domain|server|database|stack|team|company)\s+'
    r'(?:is|uses|runs|has|needs)'
    r')\b',
    re.I,
)


def _split_sentences(text: str) -> list[str]:
    text = re.sub(r'\s+', ' ', text or '').strip()
    if not text:
        return []

    sentences = re.split(r'(?<=[.!?])\s+', text)
    return [sentence.strip() for sentence in sentences if sentence.strip()]


def _normalize_for_dedupe(text: str) -> str:
    return re.sub(r'\s+', ' ', text.lower().translate(str.maketrans('', '', string.punctuation))).strip()


def extract_memory_candidates(message: str) -> list[str]:
    if not message or _OPT_OUT_RE.search(message) or _SENSITIVE_RE.search(message):
        return []

    candidates: list[str] = []
    explicit_match = _EXPLICIT_MEMORY_RE.search(message)
    if explicit_match:
        candidates.extend(_split_sentences(explicit_match.group(1)))
    else:
        for sentence in _split_sentences(message):
            if sentence.endswith('?'):
                continue
            if _FACT_RE.search(sentence):
                candidates.append(sentence)

    cleaned: list[str] = []
    seen: set[str] = set()
    for candidate in candidates:
        candidate = candidate.strip(' "\'`')
        candidate = re.sub(r'\s+', ' ', candidate).strip()
        if len(candidate) < 8:
            continue
        if len(candidate) > MAX_MEMORY_LENGTH:
            candidate = candidate[:MAX_MEMORY_LENGTH].rsplit(' ', 1)[0].strip()

        normalized = _normalize_for_dedupe(candidate)
        if normalized and normalized not in seen:
            cleaned.append(candidate)
            seen.add(normalized)

        if len(cleaned) >= MAX_AUTO_MEMORIES_PER_MESSAGE:
            break

    return cleaned


async def capture_user_memories(request: Request, messages: list[dict], user) -> list[str]:
    if not getattr(request.app.state.config, 'ENABLE_MEMORIES', False):
        return []
    if not getattr(request.app.state.config, 'ENABLE_AUTO_MEMORY_CAPTURE', True):
        return []
    if not user or not getattr(user, 'id', None):
        return []
    if not await has_permission(user.id, 'features.memories', request.app.state.config.USER_PERMISSIONS):
        return []

    candidates = extract_memory_candidates(get_last_user_message(messages) or '')
    if not candidates:
        return []

    cache_key = f'memories:user:{user.id}'
    existing_memories = await request.app.state.memory_cache.get(cache_key)
    if existing_memories is None:
        existing_memories = await Memories.get_memories_by_user_id(user.id) or []

    existing_normalized = {
        _normalize_for_dedupe(memory.content)
        for memory in existing_memories or []
        if getattr(memory, 'content', None)
    }

    saved: list[str] = []
    for candidate in candidates:
        normalized = _normalize_for_dedupe(candidate)
        if normalized in existing_normalized:
            continue

        try:
            memory = await create_memory_entry(request, user.id, candidate, user=user)
            if memory:
                saved.append(memory.content)
                existing_normalized.add(normalized)
        except Exception as e:
            log.debug(f'Failed to auto-capture memory: {e}')

    return saved
