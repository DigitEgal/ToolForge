"""Only used by the explicitly selected simulation/test mode."""
import json
from pathlib import Path
import sys
import time


def main():
    task, response, project = sys.argv[1], Path(sys.argv[2]), Path(sys.argv[3])
    print('SIMULATION: Bearbeite', task, flush=True)
    time.sleep(0.15)
    if task == 'normalize':
        (project / 'texttool.py').write_text('def normalize_text(text):\n    if not isinstance(text, str):\n        raise TypeError("text muss str sein")\n    return text.strip().lower()\n', encoding='utf-8')
    elif task == 'cli':
        (project / 'cli.py').write_text('import argparse\nfrom texttool import normalize_text\n\nif __name__ == "__main__":\n    parser = argparse.ArgumentParser()\n    parser.add_argument("text")\n    args = parser.parse_args()\n    print(normalize_text(args.text))\n', encoding='utf-8')
    elif task == 'export':
        (project / 'exporter.py').write_text('import json\nfrom pathlib import Path\nfrom texttool import normalize_text\n\ndef export_json(text, path):\n    Path(path).write_text(json.dumps({"text": normalize_text(text)}, ensure_ascii=False), encoding="utf-8")\n', encoding='utf-8')
        (project / 'README.md').write_text('# Textwerkzeug\n\n`normalize_text(text)` entfernt äußere Leerzeichen und schreibt klein.\nCLI: `python cli.py " HALLO "`.\n\n`export_json(text, path)` schreibt UTF-8-JSON. Fehlende Elternordner lösen FileNotFoundError aus; ein Verzeichnis als Dateiziel löst OSError aus.\n', encoding='utf-8')
    else:
        raise ValueError('Unbekannte Simulationsaufgabe')
    response.write_text(json.dumps({'schema_version': 1, 'task_id': task, 'run_id': response.stem.removeprefix('response-'),
                                   'outcome': 'changes_proposed', 'summary': 'Simulationsdateien erstellt.', 'question': '', 'answer_options': [], 'requested_files': []}), encoding='utf-8')
    print('SIMULATION: abgeschlossen', flush=True)


if __name__ == '__main__':
    main()
