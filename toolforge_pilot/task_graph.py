"""Task graph with dependencies, file conflicts, priorities and shared-file approvals."""
from __future__ import annotations

import json
import time
from collections import defaultdict
from pathlib import Path

from .core import atomic_json

GRAPH_FILE = 'task-graph.json'


def load_settings(project: Path) -> dict:
    path = Path(project) / '.toolforge' / GRAPH_FILE
    try:
        value = json.loads(path.read_text(encoding='utf-8'))
        return value if isinstance(value, dict) else {}
    except (OSError, ValueError):
        return {}


def save_settings(project: Path, value: dict) -> dict:
    atomic_json(Path(project) / '.toolforge' / GRAPH_FILE, value)
    return value


def _order(tasks: list[dict]) -> dict[str, set[str]]:
    """Ancestors per task: a shared file is safe when one task depends on the other."""
    deps = {task['id']: set(task.get('depends_on', [])) for task in tasks}

    def visit(ident, seen):
        for dep in deps.get(ident, ()):
            if dep not in seen:
                seen.add(dep)
                visit(dep, seen)
        return seen

    return {ident: visit(ident, set()) for ident in deps}


def _blocking_files(tasks: list[dict]) -> dict[str, set[str]]:
    users: dict[str, list[str]] = defaultdict(list)
    for task in tasks:
        for name in task.get('files', []):
            users[name].append(task['id'])
    ordered = _order(tasks)
    result: dict[str, set[str]] = {task['id']: set() for task in tasks}
    for name, ids in users.items():
        for index, first in enumerate(ids):
            for second in ids[index + 1:]:
                if second in ordered[first] or first in ordered[second]:
                    continue
                # Neither task waits for the other: concurrent file access needs an explicit approval.
                result[first].add(name)
                result[second].add(name)
    return result


def blocking_files(tasks: list[dict], task_id: str) -> set[str]:
    return _blocking_files(tasks).get(task_id, set())


def build(project: Path, state: dict | None) -> dict:
    if not state or not state.get('plan'):
        return {'nodes': [], 'edges': [], 'conflicts': [], 'critical_path': [], 'summary': {}}
    settings = load_settings(project)
    priorities = settings.get('priorities', {}) if isinstance(settings.get('priorities'), dict) else {}
    approvals = settings.get('approved_files', {}) if isinstance(settings.get('approved_files'), dict) else {}
    tasks = state['plan']['tasks']
    rows = state.get('tasks', {})
    verified = {task['id'] for task in tasks if rows.get(task['id'], {}).get('status') == 'VERIFIED'}
    waiting = {task['id'] for task in tasks if rows.get(task['id'], {}).get('question')}
    file_users: dict[str, list[str]] = defaultdict(list)
    for task in tasks:
        for name in task.get('files', []):
            file_users[name].append(task['id'])
    blocking = _blocking_files(tasks)
    nodes = []
    for task in tasks:
        ident = task['id']
        row = rows.get(ident, {})
        dependencies = task.get('depends_on', [])
        open_dependencies = [dep for dep in dependencies if dep not in verified]
        conflicts = sorted({name for name in task.get('files', []) if len(file_users[name]) > 1})
        blocking_conflicts = sorted(blocking.get(ident, set()))
        approved = sorted(name for name in conflicts if (approvals.get(name) or {}).get('approved'))
        approval_missing = [name for name in blocking_conflicts if name not in approved]
        blocked = bool(open_dependencies or row.get('question') or approval_missing)
        nodes.append({
            'id': ident, 'title': task.get('title', ''), 'status': row.get('status', 'OPEN'),
            'priority': int(priorities.get(ident, task.get('priority', 0)) or 0),
            'depends_on': dependencies, 'open_dependencies': open_dependencies,
            'files': task.get('files', []), 'conflicts': conflicts,
            'blocking_conflicts': blocking_conflicts, 'approved_files': approved,
            'approval_missing': approval_missing,
            'blocked': blocked, 'question': row.get('question'),
            'estimate': task.get('estimate', [1, 3]), 'weight': task.get('weight', 1),
        })
    edges = [{'from': dep, 'to': task['id']} for task in tasks for dep in task.get('depends_on', [])]
    conflict_rows = []
    for name, users in sorted(file_users.items()):
        if len(users) > 1:
            conflict_rows.append({'file': name, 'tasks': users,
                                  'blocking': any(name in blocking.get(ident, set()) for ident in users),
                                  'approved': bool((approvals.get(name) or {}).get('approved')),
                                  'note': (approvals.get(name) or {}).get('note', '')})
    order, depth = _topology(tasks)
    critical = _critical_path(nodes, order)
    ready = [node['id'] for node in nodes if not node['blocked'] and node['status'] != 'VERIFIED']
    return {
        'nodes': nodes, 'edges': edges, 'conflicts': conflict_rows, 'order': order,
        'critical_path': critical, 'ready': ready,
        'summary': {'tasks': len(nodes), 'verified': len(verified), 'waiting': len(waiting),
                    'blocked': sum(node['blocked'] for node in nodes),
                    'conflicts': len(conflict_rows),
                    'blocking_conflicts': sum(row['blocking'] for row in conflict_rows),
                    'approved_conflicts': sum(row['approved'] for row in conflict_rows),
                    'priorities': priorities,
                    'levels': depth},
    }


def _topology(tasks: list[dict]) -> tuple[list[str], dict[str, int]]:
    ids = [task['id'] for task in tasks]
    deps = {task['id']: set(task.get('depends_on', [])) for task in tasks}
    order, depth = [], {}
    while len(order) < len(ids):
        ready = [ident for ident in ids if ident not in order and deps[ident].issubset(order)]
        if not ready:
            break
        for ident in ready:
            order.append(ident)
            depth[ident] = max((depth.get(dep, 0) + 1 for dep in deps[ident]), default=0)
    return order, depth


def _critical_path(nodes: list[dict], order: list[str]) -> list[str]:
    by_id = {node['id']: node for node in nodes}
    cost = {node['id']: max(1.0, float(sum(node.get('estimate', [1, 3])) / 2)) for node in nodes}
    best: dict[str, tuple[float, list[str]]] = {}
    for ident in order:
        node = by_id[ident]
        previous = [(best[dep][0], best[dep][1]) for dep in node.get('depends_on', []) if dep in best]
        base_cost, base_path = max(previous, key=lambda row: row[0], default=(0.0, []))
        best[ident] = (base_cost + cost[ident], base_path + [ident])
    return max(best.values(), key=lambda row: row[0])[1] if best else []


def update(project: Path, state: dict | None, data: dict) -> dict:
    settings = load_settings(project)
    if 'priorities' in data:
        priorities = data.get('priorities')
        if not isinstance(priorities, dict):
            raise ValueError('Prioritäten müssen ein Objekt task_id -> 0..100 sein.')
        clean = {}
        for ident, value in priorities.items():
            if not isinstance(ident, str) or type(value) != int or not 0 <= value <= 100:
                raise ValueError('Ungültige Priorität.')
            clean[ident] = value
        settings['priorities'] = clean
    if 'approve_file' in data:
        name = data.get('approve_file')
        if not isinstance(name, str) or not name:
            raise ValueError('Dateiname fehlt.')
        approved = bool(data.get('approved', True))
        rows = settings.setdefault('approved_files', {})
        if approved:
            rows[name] = {'approved': True, 'at': time.time(), 'note': str(data.get('note', ''))[:500]}
        else:
            rows.pop(name, None)
        settings['updated_at'] = time.time()
    if 'approved_files' in data:
        names = data.get('approved_files')
        if not isinstance(names, list) or not all(isinstance(name, str) for name in names):
            raise ValueError('approved_files muss eine Liste sein.')
        settings['approved_files'] = {name: {'approved': True, 'at': time.time(), 'note': ''} for name in names}
    save_settings(project, settings)
    return build(project, state)


def approvals(project: Path, state: dict | None = None) -> set[str]:
    settings = load_settings(project)
    rows = settings.get('approved_files', {})
    tasks = {task['id']: task for task in ((state or {}).get('plan') or {}).get('tasks', [])}
    valid_files = {name for task in tasks.values() for name in task.get('files', [])}
    if not valid_files:
        return {name for name, row in rows.items() if (row or {}).get('approved')}
    return {name for name, row in rows.items() if (row or {}).get('approved') and name in valid_files}


def apply_priorities(project: Path, state: dict | None) -> None:
    """Copy graph priority overrides into the active plan in memory, without a new plan version."""
    if not state or not state.get('plan'):
        return
    settings = load_settings(project)
    priorities = settings.get('priorities', {})
    if not isinstance(priorities, dict):
        return
    for task in state['plan']['tasks']:
        if task['id'] in priorities and isinstance(priorities[task['id']], int):
            task['priority'] = priorities[task['id']]
