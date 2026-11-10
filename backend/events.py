"""Server-sent-event hub: session snapshots and global question notifications."""
from __future__ import annotations

import json
import queue
import threading
import time

HEARTBEAT_SECONDS = 15


class EventHub:
    def __init__(self):
        self.lock = threading.Lock()
        self.global_subscribers: set[queue.Queue] = set()
        self.session_subscribers: dict[str, set[queue.Queue]] = {}
        self.last_questions = ''

    def subscribe_global(self) -> queue.Queue:
        channel = queue.Queue(maxsize=32)
        with self.lock:
            self.global_subscribers.add(channel)
        return channel

    def unsubscribe_global(self, channel: queue.Queue) -> None:
        with self.lock:
            self.global_subscribers.discard(channel)

    def subscribe_session(self, session_id: str) -> queue.Queue:
        channel = queue.Queue(maxsize=64)
        with self.lock:
            self.session_subscribers.setdefault(session_id, set()).add(channel)
        return channel

    def unsubscribe_session(self, session_id: str, channel: queue.Queue) -> None:
        with self.lock:
            rows = self.session_subscribers.get(session_id)
            if rows:
                rows.discard(channel)
                if not rows:
                    self.session_subscribers.pop(session_id, None)

    def publish_session(self, session_id: str, event: str, data: dict) -> None:
        payload = {'event': event, 'data': data, 'at': time.time()}
        with self.lock:
            rows = list(self.session_subscribers.get(session_id, ()))
        for channel in rows:
            _put(channel, payload)

    def publish_global(self, event: str, data: dict) -> None:
        payload = {'event': event, 'data': data, 'at': time.time()}
        with self.lock:
            rows = list(self.global_subscribers)
        for channel in rows:
            _put(channel, payload)

    def publish_questions(self, digest: list[dict]) -> None:
        key = json.dumps(digest, sort_keys=True, ensure_ascii=False)
        if key == self.last_questions:
            return
        self.last_questions = key
        self.publish_global('questions', {'questions': digest, 'count': len(digest), 'at': time.time()})


def _put(channel: queue.Queue, payload: dict) -> None:
    try:
        channel.put_nowait(payload)
    except queue.Full:
        try:
            channel.get_nowait()
            channel.put_nowait(payload)
        except queue.Empty:
            pass


def sse(event: str, data: dict | str) -> str:
    if not isinstance(data, str):
        data = json.dumps(data, ensure_ascii=False)
    lines = [line for line in data.splitlines() or ['']]
    return f'event: {event}\n' + ''.join(f'data: {line}\n' for line in lines) + '\n'


def stream(channel: queue.Queue, initial: list[tuple[str, dict]] | None = None,
           stop_check=lambda: False, heartbeat: bool = True):
    """Blocking generator used by FastAPI StreamingResponse.

    Queue reads are short; a heartbeat keeps proxies and browsers from timing out.
    """
    for event, data in initial or []:
        yield sse(event, data)
    last = time.monotonic()
    while not stop_check():
        try:
            payload = channel.get(timeout=0.3)
        except queue.Empty:
            if heartbeat and time.monotonic() - last >= HEARTBEAT_SECONDS:
                last = time.monotonic()
                yield ': heartbeat\n\n'
            continue
        last = time.monotonic()
        yield sse(payload['event'], payload['data'])
