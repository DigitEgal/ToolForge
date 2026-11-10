"""Operations: project transfer, log rotation, plan backups and installer/tray status."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import shutil
import tempfile
import time
import zipfile

from .core import APP_ROOT, atomic_json, contained, safe_relative, SKIP_DIRS
from .planning import list_backups

TRANSFER_VERSION = 1
MAX_ARCHIVE = 300 * 1024 * 1024
MAX_ARCHIVE_FILES = 30000


def rotate_file(path: Path, max_bytes: int = 2_000_000, backups: int = 3) -> bool:
    path = Path(path)
    try:
        if not path.is_file() or path.stat().st_size <= max_bytes:
            return False
    except OSError:
        return False
    for number in range(backups - 1, 0, -1):
        old = path.with_name(path.name + f'.{number}')
        if old.exists():
            old.replace(path.with_name(path.name + f'.{number + 1}'))
    try:
        path.replace(path.with_name(path.name + '.1'))
        return True
    except OSError:
        return False


def rotate_diagnostics(project: Path) -> dict:
    folder = Path(project) / '.toolforge'
    rotated = []
    for relative, limit in (('diagnostics/errors.jsonl', 5_000_000),
                            ('websearch.jsonl', 2_000_000),
                            ('installations.json', 5_000_000)):
        if rotate_file(folder / relative, limit, 3):
            rotated.append(relative)
    logs = folder / 'logs'
    if logs.is_dir():
        for path in logs.glob('*.log'):
            if rotate_file(path, 10_000_000, 2):
                rotated.append(path.relative_to(folder).as_posix())
    return {'rotated': rotated, 'at': time.time()}


def _include(name: str) -> bool:
    parts = Path(name).parts
    if any(part in SKIP_DIRS for part in parts):
        return False
    if any(part.startswith(('.env', '.aider')) for part in parts):
        return False
    if name.endswith(('.pyc', '.db', '.db-wal', '.db-shm')):
        return False
    return True


def export_project(project: Path, target: Path | None = None) -> Path:
    project = Path(project).resolve()
    target = Path(target) if target else Path(tempfile.gettempdir()) / f'toolforge-{project.name}-{time.strftime("%Y%m%d-%H%M%S")}.zip'
    target.parent.mkdir(parents=True, exist_ok=True)
    manifest = {'schema_version': TRANSFER_VERSION, 'name': project.name, 'created_at': time.time(),
                'source': str(project), 'files': []}
    with zipfile.ZipFile(target, 'w', zipfile.ZIP_DEFLATED, allowZip64=True) as archive:
        for parent, dirs, names in os.walk(project):
            dirs[:] = sorted(d for d in dirs if d not in SKIP_DIRS and not (Path(parent) / d).is_symlink())
            for name in sorted(names):
                file = Path(parent) / name
                relative = file.relative_to(project).as_posix()
                if file.is_symlink() or not _include(relative):
                    continue
                try:
                    data = file.read_bytes()
                except OSError:
                    continue
                archive.writestr(relative, data)
                manifest['files'].append({'path': relative, 'sha256': hashlib.sha256(data).hexdigest(),
                                          'size': len(data)})
        archive.writestr('toolforge-transfer.json', json.dumps(manifest, ensure_ascii=False, indent=2))
    return target


def _safe_member(name: str, project: Path) -> Path:
    relative = safe_relative(name)
    target = (project / relative).resolve()
    if not target.is_relative_to(project.resolve()):
        raise ValueError('Archivpfad verlässt das Projekt.')
    return target


def import_project(source: Path, project: Path, overwrite: bool = False) -> dict:
    source, project = Path(source), Path(project).resolve()
    project.mkdir(parents=True, exist_ok=True)
    if project.exists() and any(project.iterdir()) and not overwrite:
        raise ValueError('Zielordner ist nicht leer. Import mit overwrite bestätigen.')
    with zipfile.ZipFile(source) as archive:
        infos = archive.infolist()
        if len(infos) > MAX_ARCHIVE_FILES:
            raise ValueError('Archiv enthält zu viele Dateien.')
        if sum(info.file_size for info in infos) > MAX_ARCHIVE:
            raise ValueError('Archiv ist entpackt zu groß.')
        manifest = None
        for info in infos:
            if info.filename == 'toolforge-transfer.json':
                manifest = json.loads(archive.read(info).decode('utf-8'))
                continue
            if info.is_dir():
                continue
            target = _safe_member(info.filename, project)
            if target.exists() and not overwrite:
                raise ValueError('Datei existiert bereits: ' + info.filename)
            target.parent.mkdir(parents=True, exist_ok=True)
            with archive.open(info) as reader, target.open('wb') as writer:
                shutil.copyfileobj(reader, writer)
        if not isinstance(manifest, dict) or manifest.get('schema_version') != TRANSFER_VERSION:
            raise ValueError('ToolForge-Transfermanifest fehlt oder ist ungültig.')
    return {'imported': True, 'files': len(manifest.get('files', [])), 'name': manifest.get('name'),
            'created_at': manifest.get('created_at'), 'folder': str(project)}


def installer_status() -> dict:
    iss = APP_ROOT / 'installer' / 'ToolForge.iss'
    build = APP_ROOT / 'installer' / 'build_installer.ps1'
    signtool = shutil.which('signtool') or shutil.which('signtool.exe')
    certificate = os.environ.get('TOOLFORGE_SIGN_CERT', '')
    return {
        'installer_definition': iss.is_file(), 'build_script': build.is_file(),
        'inno_setup_available': bool(shutil.which('ISCC') or shutil.which('iscc')),
        'signtool_available': bool(signtool), 'certificate_configured': bool(certificate),
        'signed': bool(signtool and certificate),
        'note': ('Signatur ist über TOOLFORGE_SIGN_CERT und einen installierten signtool-Store vorbereitet; '
                 'ohne Zertifikat wird ein unsignierter Installer gebaut.'),
    }


def tray_status() -> dict:
    try:
        import pystray  # noqa: F401
        from PIL import Image  # noqa: F401
        available = True
    except Exception:
        available = False
    return {'available': available, 'optional_file': 'requirements-tray.txt',
            'note': 'Tray ist optional. Installieren mit: pip install -r requirements-tray.txt'}


def operations_status(project: Path | None) -> dict:
    result = {'installer': installer_status(), 'tray': tray_status(), 'at': time.time()}
    if project:
        result['plan_backups'] = list_backups(project)
        result['diagnostics_folder'] = str(Path(project) / '.toolforge' / 'diagnostics')
        result['log_rotation'] = {'errors.jsonl': '5 MB / 3 Sicherungen', 'logs/*.log': '10 MB / 2 Sicherungen'}
    return result
