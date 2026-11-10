"""Application-level acceptance: CLI/HTTP/headless-browser scenarios and test-change review.

Declared plan checks remain necessary, but they are not sufficient. A finished tool
is exercised as an application. Test-file changes are reported separately and can
be explicitly reviewed.
"""
from __future__ import annotations

import difflib
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import time
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

from .core import contained, run_process, safe_relative, atomic_json, SKIP_DIRS

MAX_OUTPUT = 120_000
TEST_PATTERNS = ('test_', '_test.', 'tests/', '/tests/', 'spec.', '.spec.', '/__tests__/')


def _hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_files(project: Path) -> list[Path]:
    result = []
    for parent, dirs, names in os.walk(project):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS and d not in ('node_modules', '.venv', 'venv')]
        for name in names:
            path = Path(parent) / name
            relative = path.relative_to(project).as_posix()
            lowered = relative.lower()
            if path.is_symlink() or path.suffix.lower() not in ('.py', '.js', '.jsx', '.ts', '.tsx', '.json', '.yml', '.yaml'):
                continue
            if any(pattern in '/' + lowered for pattern in TEST_PATTERNS) or lowered.startswith('tests/'):
                result.append(path)
    return sorted(result)


def snapshot_tests(project: Path) -> dict:
    rows = {}
    for path in test_files(project):
        try:
            rows[path.relative_to(project).as_posix()] = {'sha256': _hash(path), 'size': path.stat().st_size}
        except OSError:
            continue
    return rows


def test_changes(project: Path, baseline: dict | None) -> dict:
    current = snapshot_tests(project)
    baseline = baseline or {}
    added = sorted(set(current) - set(baseline))
    removed = sorted(set(baseline) - set(current))
    changed = sorted(name for name in set(current) & set(baseline)
                     if current[name]['sha256'] != (baseline.get(name) or {}).get('sha256'))
    diffs = []
    for name in changed[:20]:
        try:
            old = contained(project, '.toolforge/test-baseline/' + name)
            new = contained(project, name)
            old_text = old.read_text(encoding='utf-8', errors='replace') if old.is_file() else ''
            new_text = new.read_text(encoding='utf-8', errors='replace') if new.is_file() else ''
            diff = list(difflib.unified_diff(old_text.splitlines(), new_text.splitlines(),
                                             fromfile=name + ' (Planbasis)', tofile=name, lineterm=''))
            diffs.append({'path': name, 'diff': '\n'.join(diff)[:20000]})
        except (OSError, ValueError, UnicodeError):
            diffs.append({'path': name, 'diff': ''})
    return {'added': added, 'removed': removed, 'changed': changed, 'diffs': diffs,
            'current': current, 'review_required': bool(added or removed or changed)}


def save_test_baseline(project: Path) -> dict:
    baseline = snapshot_tests(project)
    folder = Path(project) / '.toolforge' / 'test-baseline'
    if folder.is_dir():
        shutil.rmtree(folder, ignore_errors=True)
    for name in baseline:
        source = contained(project, name)
        target = folder / safe_relative(name)
        target.parent.mkdir(parents=True, exist_ok=True)
        try:
            shutil.copy2(source, target)
        except OSError:
            pass
    return baseline


def _local_url(url: str) -> str:
    parsed = urlsplit(str(url))
    if parsed.scheme not in ('http', 'https') or parsed.hostname not in ('127.0.0.1', 'localhost', '::1'):
        raise ValueError('Anwendungsszenarien dürfen nur lokale HTTP-Adressen öffnen.')
    return str(url)


def _browser_binary() -> str | None:
    if os.name == 'nt':
        candidates = []
        for variable in ('PROGRAMFILES', 'PROGRAMFILES(X86)', 'LOCALAPPDATA'):
            base = os.environ.get(variable)
            if base:
                candidates += [Path(base) / 'Google/Chrome/Application/chrome.exe',
                               Path(base) / 'Microsoft/Edge/Application/msedge.exe']
        return next((str(path) for path in candidates if path.is_file()), None)
    for name in ('google-chrome', 'chromium', 'chromium-browser', 'microsoft-edge'):
        found = shutil.which(name)
        if found:
            return found
    return None


def _visible_text(html: str) -> str:
    html = re.sub(r'(?is)<(script|style|noscript)[^>]*>.*?</\1>', ' ', html)
    html = re.sub(r'(?s)<[^>]+>', ' ', html)
    html = re.sub(r'&nbsp;', ' ', html)
    html = re.sub(r'&amp;', '&', html)
    return re.sub(r'\s+', ' ', html).strip()


def _run_cli(project: Path, python: str, scenario: dict, stop) -> dict:
    argv = scenario.get('argv')
    if not isinstance(argv, list) or not argv or not all(isinstance(item, str) and item for item in argv):
        raise ValueError('CLI-Szenario benötigt eine nichtleere argv-Liste.')
    argv = [item.replace('{python}', python).replace('{project}', str(project)) for item in argv]
    cwd = contained(project, str(scenario.get('cwd', '.')), True)
    timeout = int(scenario.get('timeout', 120))
    if not 1 <= timeout <= 1800:
        raise ValueError('Szenario-Timeout: 1 bis 1.800 Sekunden.')
    result = run_process(argv, cwd, timeout, stop)
    output = result.get('output', '')[:MAX_OUTPUT]
    expected = str(scenario.get('expect_text', ''))
    expected_code = scenario.get('expect_code', 0)
    passed = (result.get('code') == expected_code and not result.get('reason')
              and expected in output)
    return {'kind': 'cli', 'argv': argv, 'code': result.get('code'), 'reason': result.get('reason', ''),
            'seconds': result.get('seconds'), 'output': output, 'expect_text': expected,
            'passed': passed}


def _run_http(scenario: dict) -> dict:
    url = _local_url(str(scenario.get('url', '')))
    request = Request(url, headers={'User-Agent': 'ToolForge-Acceptance/1.1'})
    start = time.monotonic()
    try:
        with urlopen(request, timeout=int(scenario.get('timeout', 30))) as response:
            raw = response.read(500_001)
            text = raw.decode('utf-8', errors='replace')[:MAX_OUTPUT]
            expected = str(scenario.get('expect_text', ''))
            return {'kind': 'http', 'url': url, 'status': response.status,
                    'seconds': round(time.monotonic() - start, 3), 'expect_text': expected,
                    'passed': expected in text and 200 <= response.status < 400,
                    'output': _visible_text(text)[:8000]}
    except Exception as exc:
        return {'kind': 'http', 'url': url, 'error': str(exc), 'passed': False}


def _run_browser(scenario: dict) -> dict:
    url = _local_url(str(scenario.get('url', '')))
    binary = _browser_binary()
    if not binary:
        return {'kind': 'browser', 'url': url, 'passed': False,
                'error': 'Kein Chrome/Edge für die headless Browser-Abnahme gefunden.'}
    folder = Path(tempfile.mkdtemp(prefix='toolforge-browser-'))
    try:
        args = [binary, '--headless=new', '--disable-gpu', '--no-first-run', '--no-default-browser-check',
                '--disable-extensions', '--user-data-dir=' + str(folder), '--dump-dom', url]
        if os.name != 'nt':
            args.insert(1, '--no-sandbox')
        result = subprocess.run(args, capture_output=True, text=True, encoding='utf-8', errors='replace',
                                timeout=int(scenario.get('timeout', 60)))
        text = _visible_text(result.stdout)
        expected = str(scenario.get('expect_text', ''))
        return {'kind': 'browser', 'url': url, 'code': result.returncode,
                'expect_text': expected, 'passed': expected in text and result.returncode == 0,
                'output': text[:8000]}
    except Exception as exc:
        return {'kind': 'browser', 'url': url, 'error': str(exc), 'passed': False}
    finally:
        shutil.rmtree(folder, ignore_errors=True)


def declared(project: Path, plan: dict) -> list[dict]:
    rows = plan.get('acceptance_scenarios', [])
    if not isinstance(rows, list):
        raise ValueError('acceptance_scenarios muss eine Liste sein.')
    result = []
    for index, row in enumerate(rows[:12]):
        if not isinstance(row, dict) or row.get('kind') not in ('cli', 'http', 'browser'):
            raise ValueError(f'Ungültiges Anwendungsszenario {index + 1}.')
        result.append({**row, 'id': str(row.get('id') or f'scenario-{index + 1}')})
    if result:
        return result
    # Informational fallback: exercise a conventional CLI entry point, but do not
    # pretend that a missing --help implementation is a functional failure.
    for candidate in ('main.py', 'app.py', 'cli.py'):
        if contained(project, candidate).is_file():
            return [{'id': 'auto-cli-help', 'kind': 'cli', 'argv': ['{python}', candidate, '--help'],
                     'cwd': '.', 'timeout': 30, 'expect_code': 0, 'expect_text': '',
                     'informational': True, 'auto': True}]
    return []


def run(project: Path, python: str, stop, log, state: dict | None = None) -> dict:
    project = Path(project)
    plan = (state or {}).get('plan') or {}
    scenarios = declared(project, plan)
    if not scenarios:
        raise ValueError('Kein Anwendungsszenario deklariert und kein main.py/app.py/cli.py gefunden. '
                         'Im Plan acceptance_scenarios ergänzen.')
    results = []
    for scenario in scenarios:
        if stop.is_set():
            break
        log(f"\nABNAHME-SZENARIO: {scenario['id']} · {scenario['kind']}\n")
        try:
            if scenario['kind'] == 'cli':
                result = _run_cli(project, python, scenario, stop)
            elif scenario['kind'] == 'http':
                result = _run_http(scenario)
            else:
                result = _run_browser(scenario)
        except Exception as exc:
            result = {'kind': scenario.get('kind'), 'error': str(exc), 'passed': False}
        result['id'] = scenario['id']
        result['informational'] = bool(scenario.get('informational'))
        result['auto'] = bool(scenario.get('auto'))
        results.append(result)
        log(('BESTANDEN' if result.get('passed') else 'NICHT BESTANDEN') + ': ' + scenario['id'] + '\n')
    changes = test_changes(project, (state or {}).get('test_baseline'))
    hard = [row for row in results if not row.get('informational')]
    passed = bool(hard) and all(row.get('passed') for row in hard)
    report = {'at': time.time(), 'scenarios': results, 'test_changes': changes,
              'passed': passed, 'review_required': bool(changes.get('review_required')),
              'reviewed_at': None}
    atomic_json(project / '.toolforge' / 'scenarios' / 'last.json', report)
    return report


def mark_reviewed(project: Path, note: str = '') -> dict:
    path = Path(project) / '.toolforge' / 'scenarios' / 'last.json'
    if not path.is_file():
        raise ValueError('Noch keine Anwendungsabnahme vorhanden.')
    report = json.loads(path.read_text(encoding='utf-8'))
    if not report.get('review_required'):
        raise ValueError('Keine Teständerungen zu prüfen.')
    report.update(reviewed_at=time.time(), review_note=str(note)[:2000])
    atomic_json(path, report)
    return report


def last(project: Path) -> dict | None:
    path = Path(project) / '.toolforge' / 'scenarios' / 'last.json'
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return None
