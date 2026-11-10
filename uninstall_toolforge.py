"""Deinstallation von ToolForge Pilot.

Entfernt ausschliesslich ToolForge-eigene Umgebungen, Buildartefakte und Caches.
Projektordner, auf die der Pilot zeigt, werden nie angefasst. Das Programm-
verzeichnis selbst muss anschliessend manuell geloescht werden.
"""
import argparse
import os
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DATA = Path(os.environ.get('TOOLFORGE_PILOT_DATA', str(
    Path(os.environ.get('APPDATA', str(Path.home() / '.local' / 'share'))) / 'ToolForgePilot')))


def remove(path):
    path = Path(path)
    if not path.exists():
        return
    try:
        if path.is_dir() and not path.is_symlink():
            shutil.rmtree(path, onerror=lambda fn, target, _: (os.chmod(target, 0o700), fn(target)))
        else:
            path.unlink()
        print('entfernt: ' + str(path))
    except Exception as exc:
        print('konnte nicht entfernt werden: ' + str(path) + ' (' + str(exc) + ')')


def main():
    parser = argparse.ArgumentParser(description='ToolForge Pilot deinstallieren')
    parser.add_argument('--yes', action='store_true', help='ohne Rueckfragen deinstallieren')
    parser.add_argument('--keep-data', action='store_true', help='gespeicherte Projektdaten und Einstellungen behalten')
    args = parser.parse_args()
    print('ToolForge Pilot wird deinstalliert. Programmordner: ' + str(ROOT))
    print('Eigene Projektordner werden nicht veraendert.')
    try:
        if Path(sys.executable).resolve().is_relative_to((ROOT / '.venv').resolve()):
            print('Hinweis: Das Skript laeuft mit der Projekt-Python. Die .venv kann deshalb gesperrt sein;')
            print('         Deinstallieren_ToolForge.cmd bevorzugt die System-Python aus PATH.')
    except OSError:
        pass
    if not args.yes:
        answer = input('Fortfahren? [j/N] ').strip().lower()
        if answer not in ('j', 'ja', 'y', 'yes'):
            print('Abgebrochen. Es wurde nichts geloescht.')
            return
    # Reihenfolge: zuerst grosse Umgebungen, danach verbleibende Python-Caches.
    for target in (ROOT / '.venv', ROOT / '.aider-venv', ROOT / 'frontend' / 'node_modules',
                   ROOT / 'frontend' / 'dist', ROOT / 'runtime', ROOT / '.pytest_cache'):
        remove(target)
    for cache in sorted(ROOT.rglob('__pycache__'), key=lambda p: len(p.parts), reverse=True):
        remove(cache)
    if not args.keep_data:
        if args.yes or input(f' Auch gespeicherte Daten unter {DATA} loeschen? [j/N] ').strip().lower() in ('j', 'ja', 'y', 'yes'):
            remove(DATA)
        else:
            print('gespeicherte Daten behalten: ' + str(DATA))
    print('\nFertig. Loesche jetzt den Programmordner manuell: ' + str(ROOT))
    print('Falls der Ordner gesperrt ist: zuerst alle ToolForge-Fenster und CMD-Fenster schliessen.')


if __name__ == '__main__':
    main()
