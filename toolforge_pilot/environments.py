"""Reproducible environment locks and portable model/run presets."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time
from importlib import metadata

from .core import APP_ROOT, atomic_json, data_root
from .profiles import profile

AIDER_LOCK = 'requirements-aider.txt'
PRESET_VERSION = 1


def _req_pins(path: Path) -> list[dict]:
    rows = []
    if not path.is_file():
        return rows
    for line in path.read_text(encoding='utf-8').splitlines():
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        match = re.fullmatch(r'([A-Za-z0-9_.-]+)==([A-Za-z0-9.+_-]+)', line)
        if match:
            rows.append({'name': match.group(1), 'version': match.group(2),
                         'installed': _installed(match.group(1))})
    return rows


def _installed(name: str) -> str | None:
    try:
        return metadata.version(name)
    except metadata.PackageNotFoundError:
        return None


def _aider_version(python: str | None) -> str | None:
    lock = data_root() / 'aider-lock.json'
    try:
        value = json.loads(lock.read_text(encoding='utf-8'))
        if value.get('version'):
            return str(value['version'])
    except (OSError, ValueError):
        pass
    if not python or not Path(python).is_file():
        return None
    try:
        flags = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
        result = subprocess.run([python, '-m', 'aider', '--version'], capture_output=True, text=True,
                                encoding='utf-8', errors='replace', timeout=45, creationflags=flags)
        match = re.search(r'(\d+\.\d+\.\d+)', result.stdout)
        return match.group(1) if match and result.returncode == 0 else None
    except Exception:
        return None


def _docker_digest(tag: str = 'toolforge-project:latest') -> dict:
    docker = shutil.which('docker')
    if not docker:
        return {'available': False, 'tag': tag, 'image_id': None, 'repo_digests': []}
    try:
        result = subprocess.run([docker, 'image', 'inspect', tag, '--format',
                                 '{{.Id}}|{{json .RepoDigests}}|{{.Created}}'],
                                capture_output=True, text=True, timeout=20)
        if result.returncode:
            return {'available': True, 'tag': tag, 'image_id': None, 'repo_digests': [],
                    'note': 'Projektimage noch nicht gebaut.'}
        image_id, digests, created = (result.stdout.strip().split('|') + ['', '', ''])[:3]
        return {'available': True, 'tag': tag, 'image_id': image_id,
                'repo_digests': json.loads(digests or '[]'), 'created': created}
    except Exception as exc:
        return {'available': True, 'tag': tag, 'error': str(exc)}


def lock_report(aider_python: str | None = None, docker_tag: str = 'toolforge-project:latest') -> dict:
    controller = _req_pins(APP_ROOT / 'requirements-tested.txt')
    aided = _req_pins(APP_ROOT / AIDER_LOCK)
    value = {
        'schema_version': 1, 'generated_at': time.time(),
        'controller': {'python': sys.version.split()[0], 'requirements': controller,
                       'requirements_tested_sha256': _file_hash(APP_ROOT / 'requirements-tested.txt')},
        'aider': {'python': aider_python or '', 'pinned': aided,
                  'installed_version': _aider_version(aider_python),
                  'requirements_sha256': _file_hash(APP_ROOT / AIDER_LOCK)},
        'docker': _docker_digest(docker_tag),
        'presets_folder': str(data_root() / 'presets'),
        'reproducible': bool(controller and aided),
        'note': 'Lockfiles bind controller and Aider packages. Docker digests are recorded for the local project image; '
                'the base image digest is part of the build log if the registry supplies it.',
    }
    runtime = APP_ROOT / 'runtime'
    runtime.mkdir(exist_ok=True)
    try:
        atomic_json(runtime / 'environment-lock.json', value)
    except OSError:
        pass
    return value


def _file_hash(path: Path) -> str:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError:
        return ''


def export_preset(settings: dict, state: dict | None, lock: dict, name: str = 'preset') -> dict:
    clean = {key: value for key, value in settings.items() if key != 'api_key'}
    tasks = []
    if state and state.get('plan'):
        seen = set()
        for task in state['plan']['tasks']:
            for requirement in task.get('requirements', []):
                token = json.dumps(requirement, sort_keys=True)
                if token not in seen:
                    seen.add(token)
                    tasks.append(requirement)
    safe = re.sub(r'[^A-Za-z0-9_.-]+', '-', name.strip())[:60] or 'preset'
    payload = {
        'schema_version': PRESET_VERSION, 'name': safe, 'created_at': time.time(),
        'settings': clean, 'model_profile': profile(clean),
        'task_requirements': tasks, 'lock': lock,
        'target': {'platform': sys.platform, 'python': sys.version.split()[0]},
    }
    folder = data_root() / 'presets'
    folder.mkdir(parents=True, exist_ok=True)
    atomic_json(folder / (safe + '.json'), payload)
    return payload


def import_preset(payload: dict) -> dict:
    if not isinstance(payload, dict) or payload.get('schema_version') != PRESET_VERSION:
        raise ValueError('Unbekanntes Preset-Format.')
    settings = payload.get('settings')
    if not isinstance(settings, dict):
        raise ValueError('Preset enthält keine Einstellungen.')
    forbidden = {'api_key'}
    clean = {key: value for key, value in settings.items() if key not in forbidden}
    return {'settings': clean, 'name': str(payload.get('name', 'importiert'))[:60],
            'task_requirements': payload.get('task_requirements', []),
            'created_at': payload.get('created_at'), 'lock': payload.get('lock', {})}


def list_presets() -> list[dict]:
    folder = data_root() / 'presets'
    if not folder.is_dir():
        return []
    rows = []
    for path in sorted(folder.glob('*.json'), reverse=True):
        try:
            value = json.loads(path.read_text(encoding='utf-8'))
        except (OSError, ValueError):
            continue
        rows.append({'file': path.name, 'name': value.get('name'), 'created_at': value.get('created_at'),
                     'model': (value.get('settings') or {}).get('model')})
    return rows
