"""Explicit per-manager policy, validated package requests and an append-only audit."""
import json
import os
from pathlib import Path
import re
import shutil
import sys
import time
from .core import atomic_json, run_process, contained

IMPORTS = {'pytest': 'pytest', 'fastapi': 'fastapi', 'uvicorn': 'uvicorn', 'httpx': 'httpx', 'pandas': 'pandas',
           'numpy': 'numpy', 'openpyxl': 'openpyxl', 'PIL': 'Pillow', 'yaml': 'PyYAML', 'requests': 'requests',
           'ruff': 'ruff', 'mypy': 'mypy', 'pydantic': 'pydantic', 'pytest_asyncio': 'pytest-asyncio'}


class InstallBlocked(RuntimeError):
    pass


def validate_requirement(item):
    if not isinstance(item, dict) or item.get('manager') not in ('pip', 'npm', 'npx', 'choco'):
        raise ValueError('Paketmanager muss pip, npm, npx oder choco sein.')
    manager, name = item['manager'], item.get('name', '')
    pattern = r'(?:@[a-z0-9][a-z0-9._-]*/)?[a-z0-9][a-z0-9._-]*' if manager in ('npm', 'npx') else r'[A-Za-z0-9][A-Za-z0-9._-]*'
    if not isinstance(name, str) or not re.fullmatch(pattern, name): raise ValueError('Ungültiger Paketname: ' + str(name))
    version = item.get('version', '') or ''
    if not isinstance(version, str) or (version and not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9.+_-]*', version)):
        raise ValueError('Version muss eine konkrete Versionskennung sein, keine URL oder Shell-Anweisung.')
    return {'manager': manager, 'name': name, 'version': version}


def diagnose(text, task_id=''):
    lower = text.lower()
    if any(x in lower for x in ('context length', 'context window', 'contextbudget', 'eingabetokens', 'too many tokens', 'maximum context')):
        return {'kind': 'context', 'question': f'Aufgabe {task_id}: Der Modellkontext reicht für den aktuellen Auftrag nicht. Soll ich mit kleinerem Datei-Kontext fortfahren oder möchtest du in LM Studio mehr Kontext laden?'}
    match = re.search(r"(?:No module named|ModuleNotFoundError: No module named) ['\"]?([A-Za-z_][\w.]*)", text)
    if match:
        module = match.group(1).split('.')[0]
        return {'kind': 'missing_python', 'module': module, 'package': IMPORTS.get(module),
                'question': f'Aufgabe {task_id}: Python findet das Modul „{module}“ nicht. Soll die Python-Paketfreigabe aktiviert werden, oder gehört das Modul als lokale Datei zum Projekt?'}
    match = re.search(r"Cannot find (?:package|module) ['\"](@?[\w./-]+)['\"]", text)
    if match and not match.group(1).startswith(('.', '/')):
        name = match.group(1); name = '/'.join(name.split('/')[:2]) if name.startswith('@') else name.split('/')[0]
        return {'kind': 'missing_npm', 'package': name, 'question': f'Aufgabe {task_id}: Das npm-Paket „{name}“ fehlt. npm/npx-Installation erlauben oder Projektabhängigkeiten manuell bereitstellen?'}
    if any(x in lower for x in ('401', 'unauthorized', 'invalid api key')):
        return {'kind': 'auth', 'question': 'LM Studio lehnt den API-Schlüssel ab. Welcher gültige Schlüssel soll verwendet werden? Bitte unter Einstellungen eintragen und fortsetzen.'}
    if any(x in lower for x in ('connection refused', 'actively refused', 'connection error', 'failed to establish')):
        return {'kind': 'connection', 'question': 'Der Modellserver ist nicht erreichbar. Läuft der LM-Studio-Server unter der eingestellten Adresse? Bitte Server starten oder Adresse korrigieren und fortsetzen.'}
    if 'no windows console' in lower or "can't initialize prompt toolkit" in lower:
        return {'kind': 'console', 'question': 'Aider versucht trotz Batch-Profil eine Windows-Konsole zu initialisieren. Bitte Aider-Version und ausgewählten Python-Interpreter prüfen; das Protokoll enthält den Startbefehl ohne Schlüssel.'}
    if 'timeout' in lower:
        return {'kind': 'timeout', 'question': 'Der Auftrag hat das Zeitlimit überschritten. Soll das Zeitlimit erhöht werden oder soll ein kleinerer Auftrag verwendet werden?'}
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    evidence = next((line for line in reversed(lines) if re.search(r'(Error|FAILED|AssertionError|Exception|Fehler)', line)), lines[-1] if lines else 'Kein auswertbares Ergebnis.')
    return {'kind': 'code', 'question': f'Aufgabe {task_id} konnte nach den Reparaturversuchen nicht abgeschlossen werden. Letzter Befund: {evidence[:500]} Welche fachliche Vorgabe soll bei der Korrektur gelten, oder soll mit einem anderen Modell erneut versucht werden?'}


class InstallManager:
    def __init__(self, project, python, policy, stop, log):
        self.project, self.base_python = Path(project), python
        self.policy, self.stop, self.log = policy, stop, log
        self.folder = contained(self.project, '.toolforge'); self.folder.mkdir(exist_ok=True)
        self.audit_path = self.folder / 'installations.json'
        try: self.records = json.loads(self.audit_path.read_text(encoding='utf-8'))
        except FileNotFoundError: self.records = []
        if not isinstance(self.records, list): raise ValueError('Installationsjournal ist beschädigt.')

    @property
    def python(self):
        candidate = self.project / '.venv' / ('Scripts/python.exe' if os.name == 'nt' else 'bin/python')
        return str(candidate) if candidate.is_file() else self.base_python

    def enabled(self, manager):
        return bool(self.policy.get('allow_' + ('npm' if manager == 'npx' else manager), False))

    def record(self, item, argv, result):
        row = {**item, 'at': time.strftime('%Y-%m-%dT%H:%M:%S%z'), 'argv': argv,
               'success': result['code'] == 0 and not result['reason'], 'exit_code': result['code'],
               'detail': result['output'][-3000:], 'environment': self.python}
        self.records.append(row); atomic_json(self.audit_path, self.records)
        self.summary()
        return row

    def summary(self):
        header = '<!-- TOOLFORGE-INSTALLATIONS:START -->'; footer = '<!-- TOOLFORGE-INSTALLATIONS:END -->'
        lines = ['## Automatische Paketinstallationen', '', '| Zeitpunkt | Manager | Paket | Version angefordert | Ergebnis |', '|---|---|---|---|---|']
        for row in self.records:
            esc = lambda x: str(x).replace('|', '/').replace('\n', ' ')
            lines.append('| ' + ' | '.join(map(esc, [row['at'], row['manager'], row['name'], row.get('version') or 'nicht festgelegt', 'erfolgreich' if row['success'] else 'fehlgeschlagen'])) + ' |')
        block = '\n'.join(lines) + '\n'
        (self.folder / 'INSTALLATIONS.md').write_text(block, encoding='utf-8')
        readme = contained(self.project, 'README.md')
        existing = readme.read_text(encoding='utf-8') if readme.exists() else '# Projekt\n'
        region = header + '\n\n' + block + '\n' + footer
        if header in existing and footer in existing:
            existing = existing.split(header)[0] + region + existing.split(footer, 1)[1]
        else: existing = existing.rstrip() + '\n\n' + region + '\n'
        readme.write_text(existing, encoding='utf-8')

    def install(self, requirement, force=False):
        item = validate_requirement(requirement)
        if not self.enabled(item['manager']): raise InstallBlocked(f"Installation von {item['name']} benötigt die Freigabe für {item['manager']}. In Einstellungen aktivieren oder das Paket selbst installieren.")
        # At most one identical attempt per run. Persisted failures are not silently retried forever.
        if not force and any(all(row.get(k) == item[k] for k in item) and row['success'] for row in self.records):
            return False
        manager, name, version = item['manager'], item['name'], item['version']
        if manager == 'pip':
            if self.python == self.base_python:
                result = run_process([self.base_python, '-m', 'venv', str(self.project / '.venv')], self.project, 180, self.stop, self.log)
                if result['code'] != 0 or result['reason']:
                    self.record({'manager': 'pip', 'name': '(venv)', 'version': ''}, [self.base_python, '-m', 'venv', '.venv'], result)
                    raise InstallBlocked('Die Projektumgebung konnte nicht angelegt werden: ' + result['output'][-1200:])
            argv = [self.python, '-m', 'pip', 'install', '--disable-pip-version-check', name + ('==' + version if version else '')]
        elif manager in ('npm', 'npx'):
            npm = shutil.which('npm')
            if not npm: raise InstallBlocked('npm fehlt. Node.js installieren oder ein ausdrücklich deklariertes Chocolatey-Paket freigeben.')
            # npm.cmd cannot be executed portably with shell=False; use Node's actual npm CLI.
            if os.name == 'nt' and npm.lower().endswith('.cmd'):
                cli = Path(npm).parent / 'node_modules' / 'npm' / 'bin' / 'npm-cli.js'
                node = shutil.which('node')
                if not node or not cli.is_file(): raise InstallBlocked('npm-cli.js wurde nicht gefunden. Node.js-Installation prüfen.')
                argv = [node, str(cli)]
            else: argv = [npm]
            argv += ['install', '--no-audit', '--no-fund', '--save-dev', name + ('@' + version if version else '')]
        else:
            choco = shutil.which('choco')
            if not choco: raise InstallBlocked('Chocolatey ist nicht installiert. Es wird nicht automatisch gebootstrapped. Bitte Chocolatey bereitstellen.')
            argv = [choco, 'install', name, '--yes', '--no-progress'] + (['--version', version] if version else [])
        self.log('\nAUTOMATISCHE INSTALLATION: ' + ' '.join(argv) + '\n')
        result = run_process(argv, self.project, 600, self.stop, self.log)
        self.record(item, argv, result)
        if result['code'] != 0 or result['reason']:
            raise InstallBlocked(f"{manager}-Installation von {name} fehlgeschlagen. {result['output'][-1200:]}" + (' Administratorrechte gegebenenfalls manuell bereitstellen; keine automatische Rechteerhöhung.' if manager == 'choco' else ''))
        return True


def prepare_check(argv):
    """Checks do not install. Dependencies go through the audited manager."""
    command = Path(argv[0]).name.lower().removesuffix('.exe').removesuffix('.cmd')
    is_pip = command.startswith('pip') or ('-m' in argv and argv[argv.index('-m') + 1:argv.index('-m') + 2] == ['pip'])
    if (is_pip and any(x in argv for x in ('install', 'download'))) or (command in ('npm', 'choco', 'uv') and any(x in argv for x in ('install', 'i', 'ci', 'add', 'sync', 'upgrade'))):
        raise InstallBlocked('Installationsbefehle gehören in task.requirements, nicht in checks. Dadurch greifen Paketfreigabe und Installationsjournal.')
    if command == 'npm' and any(x in argv for x in ('exec', 'x')):
        raise InstallBlocked('Für Paketprogramme npx --no-install verwenden und das Paket in requirements deklarieren.')
    if command == 'npx':
        if any(x in argv for x in ('--yes', '-y')):
            raise InstallBlocked('npx darf in Prüfungen nichts nachinstallieren. Paket in requirements deklarieren.')
        argv = [argv[0], '--no-install', *[x for x in argv[1:] if x != '--no-install']]
    if os.name == 'nt' and command in ('npm', 'npx'):
        executable = shutil.which(argv[0])
        if executable and executable.lower().endswith('.cmd'):
            cli = Path(executable).parent / 'node_modules' / 'npm' / 'bin' / (command + '-cli.js')
            node = shutil.which('node')
            if not node or not cli.is_file(): raise InstallBlocked('Node.js/npm-Installation prüfen: CLI-Datei fehlt.')
            argv = [node, str(cli), *argv[1:]]
    return argv
