"""Optional Docker boundary with image/network management and resource controls."""
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import time
import uuid

from toolforge_pilot.core import run_process, contained, atomic_json
from toolforge_pilot.installations import validate_requirement

DEFAULT_MEMORY = '4g'
DEFAULT_CPUS = 2
DEFAULT_PIDS = 256
MAX_PORTS = 8
DAEMON_HINT = ('Docker-Daemon nicht erreichbar. Docker Desktop starten und „Linux-Container“ '
               'aktivieren; auf Windows muss die Pipe dockerDesktopLinuxEngine bereitstehen. '
               'Danach Status aktualisieren.')


def daemon_status(docker=None) -> dict:
    """Check the engine, not just the CLI. A missing daemon is the common build failure."""
    docker = docker or shutil.which('docker')
    if not docker:
        return {'available': False, 'version': '', 'error': 'Docker-CLI nicht gefunden. Docker Desktop installieren.'}
    try:
        result = subprocess.run([docker, 'info', '--format', '{{.ServerVersion}}'],
                                capture_output=True, text=True, timeout=15)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {'available': False, 'version': '', 'error': DAEMON_HINT + ' Technischer Befund: ' + str(exc)[-600:]}
    if result.returncode != 0:
        detail = (result.stderr or result.stdout or '').strip()[-1000:]
        return {'available': False, 'version': '', 'error': DAEMON_HINT + (' Befund: ' + detail if detail else '')}
    return {'available': True, 'version': (result.stdout or '').strip(), 'error': ''}


def require_daemon(docker=None) -> dict:
    state = daemon_status(docker)
    if not state['available']:
        raise ValueError(state['error'])
    return state


def project_tag(root):
    return hashlib.sha256(str(Path(root).resolve()).encode()).hexdigest()[:12]


def image_tag(root):
    return 'toolforge-project:' + project_tag(root)


def validate(settings):
    network = settings.get('sandbox_network', '')
    if not isinstance(network, str) or (network and not re.fullmatch(r'[a-z0-9][a-z0-9_-]{0,30}', network)):
        raise ValueError('Sandbox-Netzwerk: leer oder bis 31 Kleinbuchstaben/Ziffern/-/_.')
    memory = settings.get('sandbox_memory', DEFAULT_MEMORY)
    if not isinstance(memory, str) or not re.fullmatch(r'\d{1,4}(?:\.\d{1,2})?[mg]', memory.lower()):
        raise ValueError('Sandbox-Speicher: Zahl mit m oder g, z. B. 4g oder 512m.')
    cpus = settings.get('sandbox_cpus', DEFAULT_CPUS)
    try:
        cpus = float(cpus)
    except (TypeError, ValueError):
        raise ValueError('Sandbox-CPU: Zahl zwischen 0,1 und 32.')
    if not 0.1 <= cpus <= 32:
        raise ValueError('Sandbox-CPU: Zahl zwischen 0,1 und 32.')
    pids = settings.get('sandbox_pids', DEFAULT_PIDS)
    if type(pids) != int or not 16 <= pids <= 4096:
        raise ValueError('Sandbox-Prozesslimit: 16 bis 4.096.')
    parse_ports(settings.get('sandbox_ports', []))


def parse_ports(value) -> list[tuple[int, int]]:
    if value in (None, '', []):
        return []
    if isinstance(value, str):
        rows = [item.strip() for item in value.split(',') if item.strip()]
    elif isinstance(value, list):
        rows = value
    else:
        raise ValueError('Ports müssen als Liste oder Kommatext angegeben werden.')
    if len(rows) > MAX_PORTS:
        raise ValueError(f'Höchstens {MAX_PORTS} Portfreigaben.')
    result = []
    for row in rows:
        text = str(row).strip()
        match = re.fullmatch(r'(\d{2,5}):(\d{1,5})', text)
        if not match:
            raise ValueError('Portformat: Host:Container, z. B. 8000:8000.')
        host, container = int(match.group(1)), int(match.group(2))
        if not 1024 <= host <= 65535 or not 1 <= container <= 65535:
            raise ValueError('Host-Port 1024–65535, Container-Port 1–65535.')
        if (host, container) not in result:
            result.append((host, container))
    return result


def _port_args(settings) -> list[str]:
    args = []
    for host, container in parse_ports(settings.get('sandbox_ports', [])):
        # Preview ports are bound to loopback only, never exposed on the LAN.
        args += ['-p', f'127.0.0.1:{host}:{container}']
    return args


def command(root, argv, cwd, settings, name):
    validate(settings)
    docker = shutil.which('docker')
    if not docker:
        raise ValueError('Docker fehlt. Docker Desktop mit Linux-Containern starten oder Sandbox deaktivieren.')
    root = Path(root).resolve(); cwd = Path(cwd).resolve()
    if not cwd.is_relative_to(root):
        raise ValueError('Sandbox-Arbeitsverzeichnis liegt außerhalb des Projekts.')
    mapped = []
    for i, arg in enumerate(argv):
        if i == 0 and ('python' in Path(arg).name.lower()):
            mapped.append('python'); continue
        value = str(arg)
        if value == str(root) or value.startswith(str(root) + os.sep):
            value = '/workspace' + value[len(str(root)):].replace('\\', '/')
        if i == 0 and (value.startswith('/') or ':/' in value):
            raise ValueError('Sandbox benötigt einen im Container installierten Befehl.')
        mapped.append(value)
    network = 'toolforge-' + settings['sandbox_network'] if settings.get('sandbox_network') else 'none'
    args = [docker, 'run', '--rm', '--name', name, '--label', 'toolforge=true', '--network', network]
    if network != 'none':
        args += ['--network-alias', 'tf-' + project_tag(root)]
    args += ['--cap-drop', 'ALL', '--security-opt', 'no-new-privileges',
             '--memory', str(settings.get('sandbox_memory', DEFAULT_MEMORY)).lower(),
             '--cpus', str(settings.get('sandbox_cpus', DEFAULT_CPUS)),
             '--pids-limit', str(settings.get('sandbox_pids', DEFAULT_PIDS)),
             '--read-only', '--tmpfs', '/tmp:rw,size=512m',
             '-e', 'PYTHONDONTWRITEBYTECODE=1', '-e', 'HOME=/tmp']
    args += _port_args(settings)
    args += ['--mount', 'type=bind,source=' + str(root) + ',target=/workspace',
             '-w', '/workspace/' + cwd.relative_to(root).as_posix()]
    if os.name != 'nt':
        args += ['--user', str(os.getuid()) + ':' + str(os.getgid())]
    return args + [image_tag(root), *mapped]


def run(root, argv, cwd, timeout, stop, log, settings):
    if not settings.get('sandbox'):
        return run_process(argv, cwd, timeout, stop, log)
    name = 'toolforge-job-' + uuid.uuid4().hex
    args = command(root, argv, cwd, settings, name)
    log('Sandbox-Alias: tf-' + project_tag(root) + '; Netzwerk: ' + (settings.get('sandbox_network') or 'keines')
        + '; Ports: ' + (', '.join(f'{a}:{b}' for a, b in parse_ports(settings.get('sandbox_ports', []))) or 'keine') + '\n')
    try:
        return run_process(args, cwd, timeout, stop, log)
    finally:
        subprocess.run([args[0], 'rm', '-f', name], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=20)


def build(root, python, stop, log, settings):
    validate(settings)
    docker = shutil.which('docker')
    if not docker:
        raise ValueError('Docker ist nicht installiert.')
    require_daemon(docker)
    folder = contained(root, '.toolforge/docker'); folder.mkdir(parents=True, exist_ok=True)
    if not (folder / 'Dockerfile').exists():
        (folder / 'Dockerfile').write_text('FROM python:3.12-slim\nRUN pip install --no-cache-dir pytest ruff mypy\nWORKDIR /workspace\n', encoding='utf-8')
    result = run_process([docker, 'build', '-t', image_tag(root), str(folder)], root, 1200, stop, log)
    if result['code'] or result['reason']:
        return result
    if settings.get('sandbox_network'):
        ensure_network(root, settings['sandbox_network'], stop, log)
    write_docker_lock(root, docker)
    return result


def ensure_network(root, name, stop, log):
    validate({'sandbox_network': name})
    docker = shutil.which('docker')
    if not docker:
        raise ValueError('Docker ist nicht installiert.')
    require_daemon(docker)
    network = 'toolforge-' + name
    exists = subprocess.run([docker, 'network', 'inspect', network], capture_output=True, timeout=20)
    if exists.returncode:
        return run_process([docker, 'network', 'create', '--internal', '--label', 'toolforge=true', network],
                           root, 30, stop, log)
    return {'code': 0, 'reason': '', 'output': 'Netzwerk vorhanden.'}


def write_docker_lock(root, docker=None) -> dict:
    docker = docker or shutil.which('docker')
    result = {'at': time.time(), 'tag': image_tag(root), 'image_id': None, 'repo_digests': []}
    if docker:
        try:
            inspected = subprocess.run([docker, 'image', 'inspect', image_tag(root), '--format',
                                        '{{.Id}}|{{json .RepoDigests}}|{{.Created}}'],
                                       capture_output=True, text=True, timeout=20)
            if inspected.returncode == 0:
                image_id, digests, created = (inspected.stdout.strip().split('|') + ['', '', ''])[:3]
                result.update(image_id=image_id, repo_digests=json.loads(digests or '[]'), created=created)
        except Exception as exc:
            result['error'] = str(exc)
    try:
        atomic_json(Path(root) / '.toolforge' / 'docker-lock.json', result)
    except OSError:
        pass
    return result


def status(root, settings=None) -> dict:
    docker = shutil.which('docker')
    daemon = daemon_status(docker)
    result = {'docker_cli': bool(docker), 'docker_available': bool(daemon['available']),
              'daemon_available': bool(daemon['available']),
              'daemon_version': daemon.get('version', ''),
              'daemon_error': daemon.get('error', ''),
              'tag': image_tag(root), 'network': None,
              'image': None, 'networks': [], 'settings': settings or {}}
    if not daemon['available']:
        return result
    try:
        inspect = subprocess.run([docker, 'image', 'inspect', image_tag(root), '--format',
                                  '{{.Id}}|{{json .RepoDigests}}|{{.Created}}|{{.Size}}'],
                                 capture_output=True, text=True, timeout=20)
        if inspect.returncode == 0:
            image_id, digests, created, size = (inspect.stdout.strip().split('|') + ['', '', '', ''])[:4]
            result['image'] = {'tag': image_tag(root), 'id': image_id,
                               'repo_digests': json.loads(digests or '[]'), 'created': created,
                               'size': int(size) if str(size).isdigit() else None}
        network = 'toolforge-' + (settings or {}).get('sandbox_network', '') if (settings or {}).get('sandbox_network') else ''
        result['network'] = network or None
        listing = subprocess.run([docker, 'network', 'ls', '--filter', 'label=toolforge=true', '--format',
                                  '{{.Name}}|{{.Driver}}|{{.Scope}}'], capture_output=True, text=True, timeout=20)
        result['networks'] = [dict(zip(('name', 'driver', 'scope'), line.split('|')))
                              for line in listing.stdout.splitlines() if line.count('|') == 2]
    except Exception as exc:
        result['error'] = str(exc)
    return result


def remove_image(root, stop, log) -> dict:
    docker = shutil.which('docker')
    if not docker:
        raise ValueError('Docker ist nicht installiert.')
    require_daemon(docker)
    return run_process([docker, 'image', 'rm', image_tag(root)], root, 120, stop, log)


def remove_network(root, name, stop, log) -> dict:
    validate({'sandbox_network': name})
    docker = shutil.which('docker')
    if not docker:
        raise ValueError('Docker ist nicht installiert.')
    require_daemon(docker)
    return run_process([docker, 'network', 'rm', 'toolforge-' + name], root, 60, stop, log)


def install_package(root, manager: str, name: str, version: str, stop, log) -> dict:
    """Build a project-specific derived image with one audited package."""
    requirement = validate_requirement({'manager': manager, 'name': name, 'version': version})
    if requirement['manager'] not in ('pip', 'npm'):
        raise ValueError('Container-Pakete: nur pip oder npm.')
    docker = shutil.which('docker')
    if not docker:
        raise ValueError('Docker ist nicht installiert.')
    require_daemon(docker)
    folder = Path(root) / '.toolforge' / 'docker-packages' / uuid.uuid4().hex
    folder.mkdir(parents=True, exist_ok=True)
    if manager == 'pip':
        command_line = 'RUN python -m pip install --no-cache-dir ' + requirement['name'] + (('==' + version) if version else '')
    else:
        command_line = 'RUN npm install -g --no-audit --no-fund ' + requirement['name'] + (('@' + version) if version else '')
    (folder / 'Dockerfile').write_text(
        f'FROM {image_tag(root)}\n{command_line}\nWORKDIR /workspace\n', encoding='utf-8')
    log('CONTAINER-PAKET: ' + command_line.replace('RUN ', '') + '\n')
    result = run_process([docker, 'build', '-t', image_tag(root), str(folder)], Path(root), 900, stop, log)
    if result['code'] == 0 and not result['reason']:
        write_docker_lock(root, docker)
    return result
