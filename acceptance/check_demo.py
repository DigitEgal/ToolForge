"""Independent public-behavior checks, maintained outside the target project."""
import importlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile


def main():
    project, stage = Path(sys.argv[1]).resolve(), sys.argv[2]
    sys.path.insert(0, str(project))
    normal = importlib.import_module('texttool').normalize_text
    assert normal('  HALLO  ') == 'hallo'
    assert normal('  ÄÖÜ\n') == 'äöü'
    assert normal('') == ''
    try:
        normal(42)
    except TypeError:
        pass
    else:
        raise AssertionError('Nicht-Strings müssen TypeError auslösen.')
    if stage in ('cli', 'export'):
        result = subprocess.run([sys.executable, str(project / 'cli.py'), '  HALLO  '], capture_output=True, text=True, timeout=10)
        assert result.returncode == 0, result.stderr
        assert result.stdout.strip() == 'hallo', result.stdout
        result = subprocess.run([sys.executable, str(project / 'cli.py')], capture_output=True, text=True, timeout=10)
        assert result.returncode != 0, 'Fehlendes Argument muss fehlschlagen.'
    if stage == 'export':
        export = importlib.import_module('exporter').export_json
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / 'result.json'
            export('  GRÜẞE  ', target)
            assert json.loads(target.read_text(encoding='utf-8')) == {'text': 'grüße'}
            try:
                export('x', Path(tmp) / 'missing' / 'result.json')
            except FileNotFoundError:
                pass
            else:
                raise AssertionError('Fehlendes Elternverzeichnis muss FileNotFoundError auslösen.')
            try:
                export('x', Path(tmp))
            except OSError:
                pass
            else:
                raise AssertionError('Verzeichnis als Dateiziel muss OSError auslösen.')
        readme = (project / 'README.md').read_text(encoding='utf-8')
        assert 'export_json' in readme, 'Export-Dokumentation fehlt.'
    print('PASS:', stage)


if __name__ == '__main__':
    main()
