"""Versioned plan comparison, verified-impact warnings and pre-change backups."""
from __future__ import annotations

import copy
import json
from pathlib import Path
import time

from .core import atomic_json, contained, plan_hash, validate_plan

BACKUP_LIMIT = 30


def _tasks(plan: dict) -> dict[str, dict]:
    return {task['id']: task for task in plan.get('tasks', [])}


def _checks(task: dict) -> set[str]:
    return {json.dumps(check, sort_keys=True) for check in task.get('checks', [])}


def _effort(task: dict) -> list[int]:
    estimate = task.get('estimate', [1, 3])
    return [int(estimate[0]), int(estimate[1])]


def diff_plans(old: dict | None, new: dict, state: dict | None = None) -> dict:
    new = validate_plan(new)
    old = validate_plan(old) if old else None
    before, after = _tasks(old) if old else {}, _tasks(new)
    added = sorted(set(after) - set(before))
    removed = sorted(set(before) - set(after))
    changed = []
    checks_added, checks_removed = [], []
    for ident in sorted(set(before) & set(after)):
        fields = []
        for field in ('title', 'instruction', 'depends_on', 'files', 'acceptance', 'requirements', 'estimate', 'priority'):
            if before[ident].get(field) != after[ident].get(field):
                fields.append(field)
        added_checks = sorted(_checks(after[ident]) - _checks(before[ident]))
        removed_checks = sorted(_checks(before[ident]) - _checks(after[ident]))
        if added_checks:
            checks_added.extend({'task': ident, 'check': json.loads(check)} for check in added_checks)
        if removed_checks:
            checks_removed.extend({'task': ident, 'check': json.loads(check)} for check in removed_checks)
        if fields or added_checks or removed_checks:
            changed.append({'id': ident, 'fields': fields, 'checks_added': len(added_checks),
                            'checks_removed': len(removed_checks),
                            'files_before': before[ident].get('files', []),
                            'files_after': after[ident].get('files', [])})
    old_effort = sum(sum(_effort(task)) / 2 for task in before.values())
    new_effort = sum(sum(_effort(task)) / 2 for task in after.values())
    verified = {ident for ident, row in (state or {}).get('tasks', {}).items()
                if row.get('status') == 'VERIFIED' or row.get('ever_verified')}
    touched = []
    for ident in sorted(verified):
        if ident not in before:
            continue
        old_files = set(before[ident].get('files', []))
        affected = []
        for other in added + changed_ids(changed) + removed:
            task = after.get(other) or before.get(other) or {}
            if old_files.intersection(task.get('files', [])):
                affected.append(other)
        if affected:
            touched.append({'task': ident, 'files': sorted(old_files), 'affected_by': affected})
    dependency_changes = []
    for ident in sorted(set(before) & set(after)):
        if before[ident].get('depends_on') != after[ident].get('depends_on'):
            dependency_changes.append({'task': ident, 'before': before[ident].get('depends_on', []),
                                       'after': after[ident].get('depends_on', [])})
    warnings = []
    if touched:
        warnings.append('Bereits geprüfte Aufgaben teilen Dateien mit geänderten oder neuen Aufgaben.')
    if checks_removed:
        warnings.append('Prüfungen wurden entfernt oder verändert; das schwächt den Erfolgsnachweis.')
    if removed:
        warnings.append('Aufgaben wurden aus dem Plan entfernt.')
    risk = 'high' if touched or checks_removed or removed else 'medium' if changed or added else 'low'
    return {
        'old_hash': plan_hash(old) if old else None, 'new_hash': plan_hash(new),
        'old_version': old.get('version') if old else None, 'new_version': new.get('version'),
        'added': [{'id': ident, 'title': after[ident].get('title'), 'files': after[ident].get('files', []),
                   'estimate': _effort(after[ident])} for ident in added],
        'removed': [{'id': ident, 'title': before[ident].get('title'), 'files': before[ident].get('files', [])}
                    for ident in removed],
        'changed': changed,
        'checks_added': checks_added, 'checks_removed': checks_removed,
        'dependencies': dependency_changes,
        'verified_impacted': touched,
        'effort': {'before': round(old_effort, 1), 'after': round(new_effort, 1),
                   'delta': round(new_effort - old_effort, 1)},
        'task_count': {'before': len(before), 'after': len(after)},
        'risk': risk, 'warnings': warnings,
        'requires_confirmation': bool(touched or checks_removed),
    }


def changed_ids(changed: list[dict]) -> list[str]:
    return [row['id'] for row in changed]


def backup_plan(project: Path, state: dict | None, reason: str) -> Path | None:
    if not state or not state.get('plan'):
        return None
    folder = Path(project) / '.toolforge' / 'plan-backups'
    folder.mkdir(parents=True, exist_ok=True)
    stamp = time.strftime('%Y%m%d-%H%M%S') + '-' + str(time.time_ns() % 1_000_000_000)
    path = folder / f'plan-v{state["plan"].get("version", 0)}-{stamp}.json'
    atomic_json(path, {'reason': reason, 'at': time.time(), 'plan': state['plan'],
                       'tasks': state.get('tasks', {}), 'plan_hash': plan_hash(state['plan'])})
    rows = sorted(folder.glob('plan-*.json'), key=lambda p: p.name)
    for old in rows[:-BACKUP_LIMIT]:
        try:
            old.unlink()
        except OSError:
            pass
    return path


def list_backups(project: Path) -> list[dict]:
    folder = Path(project) / '.toolforge' / 'plan-backups'
    if not folder.is_dir():
        return []
    result = []
    for path in sorted(folder.glob('plan-*.json'), reverse=True):
        try:
            data = json.loads(path.read_text(encoding='utf-8'))
        except (OSError, ValueError):
            continue
        plan = data.get('plan') or {}
        result.append({'file': path.name, 'reason': data.get('reason', ''), 'at': data.get('at'),
                       'version': plan.get('version'), 'goal': plan.get('goal', '')[:300],
                       'tasks': len(plan.get('tasks', [])), 'plan_hash': data.get('plan_hash')})
    return result


def load_backup(project: Path, name: str) -> dict:
    if not name or '/' in name or '\\' in name or not name.startswith('plan-') or not name.endswith('.json'):
        raise ValueError('Ungültige Sicherungsdatei.')
    path = contained(project, '.toolforge/plan-backups/' + name)
    if not path.is_file():
        raise ValueError('Sicherung nicht gefunden.')
    data = json.loads(path.read_text(encoding='utf-8'))
    return {'plan': validate_plan(data.get('plan')), 'tasks': data.get('tasks', {}),
            'reason': data.get('reason', ''), 'at': data.get('at')}


def copy_plan(plan: dict) -> dict:
    return copy.deepcopy(validate_plan(plan))
