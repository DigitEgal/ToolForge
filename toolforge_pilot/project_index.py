"""Incremental project index: file symbols, imports, dependencies and full-context chunks.

The index is stored inside the project at .toolforge/index.json. Only changed files
are parsed again; deletions are removed. Large projects are read in bounded,
explicitly logged batches instead of silently sampling the first 500 files.
"""
from __future__ import annotations

import ast
import hashlib
import json
import os
from pathlib import Path
import re
import time
from typing import Iterable

from .core import SKIP_DIRS, atomic_json, contained

INDEX_VERSION = 1
MAX_FILES = 20000
MAX_FILE_BYTES = 2_000_000
MAX_CONTEXT_CHARS = 400_000
SOURCE_SUFFIXES = {
    '.py': 'python', '.pyi': 'python', '.js': 'javascript', '.jsx': 'javascript',
    '.mjs': 'javascript', '.cjs': 'javascript', '.ts': 'typescript', '.tsx': 'typescript',
    '.json': 'json', '.md': 'markdown', '.txt': 'text', '.html': 'html', '.htm': 'html',
    '.css': 'css', '.scss': 'css', '.yaml': 'yaml', '.yml': 'yaml', '.toml': 'toml',
    '.ini': 'ini', '.cfg': 'ini', '.sql': 'sql', '.sh': 'shell', '.ps1': 'powershell',
}
TEXT_SUFFIXES = set(SOURCE_SUFFIXES) | {'.csv'}


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _signature(stat) -> str:
    return f'{stat.st_mtime_ns}:{stat.st_size}'


def _walk(project: Path) -> list[Path]:
    result: list[Path] = []
    for parent, dirs, names in os.walk(project, followlinks=False):
        dirs[:] = sorted(d for d in dirs if d not in SKIP_DIRS and not (Path(parent) / d).is_symlink())
        for name in sorted(names):
            file = Path(parent) / name
            if file.is_symlink() or name.startswith(('.env', '.aider')) or name.endswith(('.pyc', '.db', '.db-wal', '.db-shm')):
                continue
            result.append(file)
            if len(result) >= MAX_FILES:
                return result
    return result


def _python_symbols(tree) -> list[dict]:
    rows = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            rows.append({'kind': 'function', 'name': node.name, 'line': node.lineno})
        elif isinstance(node, ast.ClassDef):
            rows.append({'kind': 'class', 'name': node.name, 'line': node.lineno})
    # Python's AST has no parent links: inspect module-level assignments explicitly.
    for node in getattr(tree, 'body', []):
        targets = node.targets if isinstance(node, ast.Assign) else [node.target] if isinstance(node, ast.AnnAssign) else []
        for target in targets:
            if isinstance(target, ast.Name) and target.id.isupper():
                rows.append({'kind': 'constant', 'name': target.id, 'line': node.lineno})
    return rows[:2000]


def _python_imports(tree) -> list[dict]:
    rows = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                rows.append({'module': alias.name, 'level': 0, 'names': [alias.asname or alias.name.split('.')[0]], 'line': node.lineno})
        elif isinstance(node, ast.ImportFrom):
            rows.append({'module': node.module or '', 'level': node.level, 'names': [a.name for a in node.names], 'line': node.lineno})
    return rows[:2000]


def _parse_python(text: str) -> tuple[list[dict], list[dict], str]:
    try:
        tree = ast.parse(text)
    except (SyntaxError, ValueError) as exc:
        return [], [], f'Syntaxfehler: {exc}'
    return _python_symbols(tree), _python_imports(tree), ''


JS_IMPORT = re.compile(r"""(?:import|export)\s+(?:[^'"]*?\s+from\s+)?['"]([^'"]+)['"]""")
JS_REQUIRE = re.compile(r"""require\(\s*['"]([^'"]+)['"]\s*\)""")
JS_SYMBOL = re.compile(r"""(?:export\s+)?(?:default\s+)?(?:async\s+)?(?:class|function|const|let|var)\s+([A-Za-z_$][\w$]*)""")


def _parse_js(text: str) -> tuple[list[dict], list[dict], str]:
    symbols = [{'kind': 'symbol', 'name': match.group(1), 'line': text[:match.start()].count('\n') + 1}
               for match in JS_SYMBOL.finditer(text)][:2000]
    imports = []
    for match in list(JS_IMPORT.finditer(text)) + list(JS_REQUIRE.finditer(text)):
        module = match.group(1)
        imports.append({'module': module, 'level': 0, 'names': [], 'line': text[:match.start()].count('\n') + 1})
    return symbols, imports[:2000], ''


def _parse_markdown(text: str) -> tuple[list[dict], list[dict], str]:
    symbols = [{'kind': 'heading', 'name': match.group(2).strip(), 'line': text[:match.start()].count('\n') + 1}
               for match in re.finditer(r'^(#{1,4})\s+(.+)$', text, re.M)][:1000]
    return symbols, [], ''


def _parse_json(text: str) -> tuple[list[dict], list[dict], str]:
    try:
        value = json.loads(text)
    except (ValueError, TypeError) as exc:
        return [], [], f'JSON-Fehler: {exc}'
    if not isinstance(value, dict):
        return [], [], ''
    symbols = [{'kind': 'key', 'name': str(key)[:120], 'line': 0} for key in list(value)[:500]]
    return symbols, [], ''


def parse_file(path: Path, relative: str) -> dict:
    stat = path.stat()
    row = {'path': relative, 'suffix': path.suffix.lower(), 'size': stat.st_size, 'signature': _signature(stat),
           'language': SOURCE_SUFFIXES.get(path.suffix.lower(), 'binary'), 'symbols': [], 'imports': [],
           'dependencies': [], 'error': '', 'lines': 0, 'sha256': ''}
    if stat.st_size > MAX_FILE_BYTES:
        row['error'] = f'Datei größer als {MAX_FILE_BYTES} Bytes; Inhalt nicht indexiert.'
        row['sha256'] = _sha(path.read_bytes()[:65536])
        return row
    try:
        data = path.read_bytes()
    except OSError as exc:
        row['error'] = f'Nicht lesbar: {exc}'
        return row
    row['sha256'] = _sha(data)
    row['lines'] = data.count(b'\n') + (1 if data else 0)
    if b'\0' in data[:8192] or path.suffix.lower() not in TEXT_SUFFIXES:
        row['language'] = 'binary'
        return row
    try:
        text = data.decode('utf-8')
    except UnicodeError:
        row['error'] = 'Nicht UTF-8; Inhalt nicht indexiert.'
        return row
    if path.suffix.lower() in ('.py', '.pyi'):
        symbols, imports, error = _parse_python(text)
    elif path.suffix.lower() in ('.js', '.jsx', '.mjs', '.cjs', '.ts', '.tsx'):
        symbols, imports, error = _parse_js(text)
    elif path.suffix.lower() == '.md':
        symbols, imports, error = _parse_markdown(text)
    elif path.suffix.lower() == '.json':
        symbols, imports, error = _parse_json(text)
    else:
        symbols, imports, error = [], [], ''
    row.update(symbols=symbols, imports=imports, error=error)
    return row


def _resolve_import(source: str, item: dict, files: set[str]) -> list[str]:
    module = str(item.get('module', '')).strip()
    if not module:
        return []
    normalized = module.replace('\\', '/')
    candidates: list[str] = []
    if normalized.startswith('.'):
        base = Path(source).parent
        parts = normalized.split('/')
        while parts and parts[0] in ('', '.'):
            parts.pop(0)
        while parts and parts[0] == '..':
            parts.pop(0)
            base = base.parent
        target = (base / '/'.join(parts)).as_posix() if parts else base.as_posix()
        candidates.append(target)
    elif module.startswith('@/') or module.startswith('~/'):
        candidates.append(module[2:])
    else:
        candidates.append(module.replace('.', '/'))
    level = int(item.get('level') or 0)
    expanded: list[str] = []
    for candidate in candidates:
        if level:
            base = Path(source).parent
            for _ in range(max(0, level - 1)):
                base = base.parent
            candidate = (base / candidate).as_posix() if candidate else base.as_posix()
        expanded.append(candidate.replace('\\', '/'))
    found = []
    for candidate in expanded:
        for suffix in ('', '.py', '.pyi', '.js', '.jsx', '.ts', '.tsx', '.mjs', '.cjs', '/__init__.py', '/index.js', '/index.ts', '/index.tsx'):
            name = (candidate + suffix).lstrip('./')
            if name in files:
                found.append(name)
                break
    return found


def load(project: Path) -> dict | None:
    path = Path(project) / '.toolforge' / 'index.json'
    if not path.is_file():
        return None
    try:
        value = json.loads(path.read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return None
    if not isinstance(value, dict) or value.get('version') != INDEX_VERSION:
        return None
    return value


def summary(index: dict) -> dict:
    files = index.get('files', {})
    sources = [row for row in files.values() if row.get('language') not in ('binary', 'unknown')]
    edges = sum(len(row.get('dependencies', [])) for row in files.values())
    return {
        'files': len(files), 'indexed': len(sources),
        'symbols': sum(len(row.get('symbols', [])) for row in files.values()),
        'dependencies': edges,
        'errors': sum(bool(row.get('error')) for row in files.values()),
        'languages': {language: sum(row.get('language') == language for row in files.values())
                      for language in sorted({row.get('language', 'unknown') for row in files.values()})},
        'truncated': len(files) >= MAX_FILES,
        'generated_at': index.get('generated_at'),
    }


def refresh(project: Path, force: bool = False) -> dict:
    project = Path(project).resolve()
    previous = load(project) or {'files': {}}
    old = previous.get('files', {})
    files: dict[str, dict] = {}
    changed, removed, unchanged = [], [], 0
    for path in _walk(project):
        relative = path.relative_to(project).as_posix()
        try:
            stat = path.stat()
        except OSError:
            continue
        row = old.get(relative)
        if not force and row and row.get('signature') == _signature(stat) and row.get('sha256'):
            files[relative] = row
            unchanged += 1
            continue
        files[relative] = parse_file(path, relative)
        changed.append(relative)
    removed = sorted(set(old) - set(files))
    names = set(files)
    for relative, row in files.items():
        deps: list[str] = []
        for item in row.get('imports', []):
            deps.extend(_resolve_import(relative, item, names))
        row['dependencies'] = sorted(set(dep for dep in deps if dep != relative))
    index = {'version': INDEX_VERSION, 'project': str(project), 'generated_at': time.time(),
             'files': files, 'last_change': {'changed': changed[:500], 'removed': removed[:500],
                                             'unchanged': unchanged, 'changed_count': len(changed),
                                             'removed_count': len(removed), 'at': time.time()}}
    index['summary'] = summary(index)
    atomic_json(project / '.toolforge' / 'index.json', index)
    return index


def _text_for(project: Path, relative: str) -> str:
    try:
        path = contained(project, relative)
        if path.stat().st_size > MAX_FILE_BYTES:
            return ''
        data = path.read_bytes()
        if b'\0' in data[:8192]:
            return ''
        return data.decode('utf-8')
    except (OSError, ValueError, UnicodeError):
        return ''


def _split_chunks(text: str, max_chars: int) -> Iterable[tuple[int, int, str]]:
    lines = text.splitlines(keepends=True)
    start, size, buffer = 1, 0, []
    for number, line in enumerate(lines, 1):
        if buffer and size + len(line) > max_chars:
            yield start, number - 1, ''.join(buffer)
            start, size, buffer = number, 0, []
        while len(line) > max_chars:
            yield number, number, line[:max_chars]
            line = line[max_chars:]
            start = number
        buffer.append(line)
        size += len(line)
    if buffer:
        yield start, max(1, len(lines)), ''.join(buffer)


def context(project: Path, max_chars: int = 40000, paths: list[str] | None = None,
            index: dict | None = None) -> dict:
    """Return a complete, chunked analysis context with explicit coverage.

    Manifest data (symbols/imports/dependencies) is always included for every file;
    source chunks are included in priority order until the budget is reached.
    """
    project = Path(project).resolve()
    max_chars = max(4000, min(int(max_chars), MAX_CONTEXT_CHARS))
    index = index or load(project) or refresh(project)
    files = index.get('files', {})
    preferred = [p for p in (paths or []) if p in files]
    rest = sorted((p for p in files if p not in preferred),
                  key=lambda name: (not name.endswith(('.py', '.ts', '.tsx', '.js', '.jsx', '.md')), name))
    order = preferred + rest
    # The manifest itself is bounded too, otherwise thousands of files would consume
    # the whole context before a single source chunk is considered.
    manifest_cap = max(4000, max_chars // 2)
    manifest_files = []
    manifest_used = 0
    for name, row in sorted(files.items()):
        entry = {'path': name, 'language': row.get('language'), 'symbols': row.get('symbols', [])[:80],
                 'imports': [item.get('module', '') for item in row.get('imports', [])][:80],
                 'dependencies': row.get('dependencies', [])[:80], 'lines': row.get('lines', 0),
                 'error': row.get('error', '')}
        cost = len(json.dumps(entry, ensure_ascii=False)) + 2
        if manifest_files and manifest_used + cost > manifest_cap:
            break
        manifest_files.append(entry)
        manifest_used += cost
    manifest = {'project': str(project), 'summary': index.get('summary', summary(index)),
                'files': manifest_files, 'files_total': len(files),
                'truncated': len(manifest_files) < len(files)}
    manifest_cost = len(json.dumps(manifest, ensure_ascii=False))
    chunks = []
    used = manifest_cost
    total_chars = 0
    included_chars = 0
    included_files: set[str] = set()
    batches = []
    for name in order:
        row = files[name]
        if row.get('language') in ('binary', 'unknown') or row.get('error', '').startswith('Datei größer'):
            continue
        text = _text_for(project, name)
        if not text:
            continue
        total_chars += len(text)
        parts = list(_split_chunks(text, 8000))
        for number, (start, end, body) in enumerate(parts, 1):
            header = f'\n### Datei {name} · Teil {number}/{len(parts)} · Zeilen {start}-{end}\n'
            block = header + body
            if used + len(block) > max_chars:
                continue
            chunks.append({'path': name, 'part': number, 'parts': len(parts), 'start_line': start,
                           'end_line': end, 'text': body, 'chars': len(body)})
            used += len(block)
            included_chars += len(body)
            included_files.add(name)
        batches.append({'file': name, 'parts': len(parts), 'included': name in included_files})
    coverage = {
        'files_total': len(files), 'files_included': len(included_files),
        'chars_total': total_chars, 'chars_included': included_chars,
        'percent': round((included_chars / total_chars * 100) if total_chars else 100, 1),
        'manifest_chars': manifest_cost, 'budget_chars': max_chars,
    }
    report = {'generated_at': time.time(), 'coverage': coverage, 'batches': batches,
              'index_summary': index.get('summary', summary(index))}
    atomic_json(project / '.toolforge' / 'analysis.json', report)
    return {'manifest': manifest, 'chunks': chunks, 'coverage': coverage, 'batches': batches}


def status(project: Path) -> dict:
    index = load(project)
    if not index:
        return {'indexed': False, 'summary': None, 'last_change': None}
    return {'indexed': True, 'summary': index.get('summary', summary(index)),
            'last_change': index.get('last_change'), 'path': '.toolforge/index.json'}
