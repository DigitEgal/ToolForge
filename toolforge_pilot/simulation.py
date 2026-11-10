"""Explicit deterministic demo, never presented as a real LLM integration test."""
from pathlib import Path
import sys
from .core import run_process


class DemoAdapter:
    model = 'SIMULATION'
    key = ''

    def run(self, project, task, prompt, run_dir, response_path, stop, log, force_whole=False):
        return run_process([sys.executable, str(Path(__file__).with_name('fake_worker.py')),
                            task['id'], str(response_path), str(project)], project, 30, stop, log)
