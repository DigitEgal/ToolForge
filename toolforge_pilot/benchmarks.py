"""Empirical model/context trials: repeated samples, tokens/s, VRAM peaks, dispersion.

Results are cached per hardware fingerprint, model quantization, task kind and
context size. The recommendation is a measured candidate for this machine, not a
claim that a model family is universally best.
"""
from __future__ import annotations

import hashlib
import json
import platform
import random
import re
import statistics
import time
from pathlib import Path

from .core import atomic_json, data_root
from .preflight import context_compatible, parse_json, signature, temperatures_for
from .profiles import estimate

CACHE_FILE = 'benchmark-cache.json'
CACHE_LIMIT = 500
MAX_REPEATS = 5


def hardware_info() -> dict:
    return {
        'system': platform.system(), 'release': platform.release(), 'machine': platform.machine(),
        'processor': platform.processor() or '', 'python': platform.python_version(),
    }


def hardware_fingerprint() -> str:
    return hashlib.sha256(json.dumps(hardware_info(), sort_keys=True).encode()).hexdigest()[:16]


def _cache_path() -> Path:
    return data_root() / CACHE_FILE


def load_cache() -> dict:
    try:
        value = json.loads(_cache_path().read_text(encoding='utf-8'))
        return value if isinstance(value, dict) else {}
    except (OSError, ValueError):
        return {}


def cache_rows() -> list[dict]:
    cache = load_cache()
    return sorted(cache.values(), key=lambda row: row.get('at', 0), reverse=True)


def _cache_key(model: str, quantization: str, kind: str, context: int, goal_signature: str) -> str:
    raw = [hardware_fingerprint(), model, quantization or 'unknown', kind, int(context), goal_signature]
    return hashlib.sha256(json.dumps(raw).encode()).hexdigest()[:32]


def _save_cache(report: dict) -> None:
    cache = load_cache()
    key = report.get('cache_key')
    if not key:
        return
    cache[key] = report
    if len(cache) > CACHE_LIMIT:
        for old in sorted(cache, key=lambda item: cache[item].get('at', 0))[:len(cache) - CACHE_LIMIT]:
            cache.pop(old, None)
    atomic_json(_cache_path(), cache)


def _numbers(value, key_hint: str, depth: int = 0):
    if depth > 6:
        return []
    found = []
    if isinstance(value, dict):
        for key, item in value.items():
            lowered = str(key).lower()
            if isinstance(item, (int, float)) and not isinstance(item, bool) and any(word in lowered for word in ('vram', 'peak', 'memory', 'size_bytes', 'size')):
                if item > 1024:  # filter tiny config values such as context_length units
                    found.append(float(item))
            else:
                found.extend(_numbers(item, key_hint, depth + 1))
    elif isinstance(value, list):
        for item in value:
            found.extend(_numbers(item, key_hint, depth + 1))
    return found


def vram_peak(instances: list[dict]) -> int | None:
    values = []
    for instance in instances:
        values.extend(_numbers(instance, 'vram'))
    return int(max(values)) if values else None


def _structural_quality(response: str, valid: bool) -> float:
    if not valid:
        return 0.0
    try:
        parsed = parse_json(response)
    except (ValueError, TypeError):
        return 10.0
    score = 30.0
    for key, weight in (('solution', 30), ('checks', 25), ('limitations', 15)):
        value = parsed.get(key)
        if isinstance(value, str) and value.strip():
            score += weight
        elif isinstance(value, list) and value:
            score += weight
    return min(100.0, score)


def _group_stats(samples: list[dict]) -> list[dict]:
    groups: dict[tuple, list[dict]] = {}
    for sample in samples:
        groups.setdefault((sample['model'], sample['context_tokens'], sample.get('quantization') or ''), []).append(sample)
    result = []
    for (model, context, quantization), rows in groups.items():
        scores = [row.get('score', 0.0) for row in rows]
        speeds = [row.get('tokens_per_second', 0.0) for row in rows if row.get('tokens_per_second')]
        vram = [row['vram_bytes'] for row in rows if row.get('vram_bytes')]
        result.append({
            'model': model, 'context_tokens': context, 'quantization': quantization,
            'samples': len(rows), 'quality_mean': round(statistics.fmean(scores), 1) if scores else 0,
            'quality_stdev': round(statistics.pstdev(scores), 1) if len(scores) > 1 else 0.0,
            'tokens_per_second': round(statistics.fmean(speeds), 1) if speeds else None,
            'vram_peak_bytes': max(vram) if vram else None,
        })
    return sorted(result, key=lambda row: (row['quality_mean'], -(row['quality_stdev'] or 0)), reverse=True)


def measure(studio, goal: str, model: str, judge: str, kind: str, contexts: list[int],
            repeats: int = 2, two_temperatures: bool = False, emit=lambda text: None,
            save=lambda report: None, force: bool = False) -> dict:
    if not goal.strip():
        raise ValueError('Aufgabenbeschreibung fehlt.')
    if kind not in ('coding', 'presentation', 'context', 'general'):
        raise ValueError('Unbekanntes Testprofil.')
    contexts = sorted({int(value) for value in contexts})
    if not contexts or len(contexts) > 4 or any(value < 4096 or value > 200000 for value in contexts):
        raise ValueError('Ein bis vier Kontextgrößen zwischen 4.096 und 200.000 Tokens.')
    if type(repeats) != int or not 1 <= repeats <= MAX_REPEATS:
        raise ValueError(f'Wiederholungen: 1 bis {MAX_REPEATS}.')
    inventory = {row['key']: row for row in studio.inventory() if row.get('type') == 'llm'}
    if model not in inventory:
        raise ValueError('Modell nicht installiert: ' + model)
    if judge and judge not in inventory:
        raise ValueError('Auswertungsmodell nicht installiert: ' + judge)
    for context in contexts:
        maximum = inventory[model].get('max_context_length')
        if maximum and context > maximum:
            raise ValueError(f'{model}: Kontext überschreitet Modelllimit {maximum}.')
    goal_signature = signature(goal)
    quantization = str(inventory[model].get('selected_variant') or inventory[model].get('quantization') or '')
    key = _cache_key(model, quantization, kind, max(contexts), goal_signature)
    if not force:
        cached = load_cache().get(key)
        if cached and cached.get('status') == 'ready':
            return {**cached, 'cached': True}
    focus = {'coding': 'Liefere einen kleinen Codeausschnitt und konkrete Tests.',
             'presentation': 'Liefere drei konkrete Folien mit Zielgruppe, Kernaussage und Sprechernotizen.',
             'context': 'Beziehe Anfang, Mitte und Ende des Materials ein; benenne Widersprüche.',
             'general': 'Liefere eine konkrete Teillösung und prüfbare Abnahmekriterien.'}[kind]
    prompt = ('Bearbeite eine repräsentative kurze Arbeitsprobe. ' + focus +
              ' Keine Selbsteinschätzung. JSON mit solution, checks, limitations.\nAUFGABE:\n' + goal)
    report = {'status': 'running', 'at': time.time(), 'goal': goal, 'goal_signature': goal_signature,
              'kind': kind, 'model': model, 'judge': judge, 'contexts': contexts, 'repeats': repeats,
              'two_temperatures': two_temperatures, 'hardware': hardware_info(),
              'hardware_fingerprint': hardware_fingerprint(), 'quantization': quantization,
              'cache_key': key, 'samples': [], 'groups': [], 'recommendation': None,
              'note': 'Arbeitsproben werden nicht ausgeführt. Qualitätswerte sind Auswertung plus Formatprüfung; VRAM wird nur gemeldet, wenn LM Studio ihn über die Native API liefert.'}
    save(report)
    try:
        sample_id = 0
        for context in contexts:
            emit('Lade ' + model + ' mit ' + str(context) + ' Tokens …')
            instance = studio.switch(model, context)
            actual = getattr(studio, 'actual_context', None)
            if type(actual) is not int:
                actual = context
            temperatures = temperatures_for(model, kind)[:2 if two_temperatures else 1]
            for temperature in temperatures:
                for attempt in range(repeats):
                    studio.check()
                    sample_id += 1
                    emit(f'Arbeitsprobe {sample_id}: {model}, {actual} Tokens, T {temperature}, Wiederholung {attempt + 1}/{repeats}')
                    sample = {'id': f'S{sample_id}', 'model': model, 'context_tokens': actual,
                              'temperature': temperature, 'attempt': attempt + 1,
                              'quantization': quantization,
                              'selected_variant': inventory[model].get('selected_variant')}
                    try:
                        result = studio.chat(instance, prompt, temperature, min(2048, actual // 4))
                        sample.update(result)
                        parsed = parse_json(result.get('response', ''))
                        # `checks` may be a single text field or a non-empty list of checks.
                        sample['valid'] = (all((isinstance(parsed.get(key), str) and parsed[key].strip())
                                               or (isinstance(parsed.get(key), list) and bool(parsed[key]))
                                               for key in ('solution', 'checks', 'limitations'))
                                           and result.get('finish_reason') != 'length')
                        sample['score'] = _structural_quality(result.get('response', ''), sample['valid'])
                        usage = result.get('usage') or {}
                        completion = usage.get('completion_tokens') if isinstance(usage, dict) else None
                        if not isinstance(completion, int) or completion <= 0:
                            completion = estimate(result.get('response', ''))
                        seconds = result.get('seconds') or 0
                        sample['tokens_per_second'] = round(completion / seconds, 1) if seconds else None
                        sample['vram_bytes'] = vram_peak(studio.instances())
                    except Exception as exc:
                        studio.check()
                        sample.update(valid=False, score=0.0, error=str(exc), tokens_per_second=None)
                    report['samples'].append(sample)
                    save(report)
        valid = [row for row in report['samples'] if row.get('valid')]
        if not valid:
            raise ValueError('Keine gültige Arbeitsprobe. Keine Empfehlung erstellt.')
        if judge:
            emit('Anonymisierte Auswertung mit ' + judge + ' …')
            blind = [{'id': row['id'], 'response': row.get('response', ''), 'context_tokens': row['context_tokens'],
                      'seconds': row.get('seconds')} for row in valid]
            random.Random(42).shuffle(blind)
            judge_prompt = ('Bewerte die anonymisierten Arbeitsproben nach Korrektheit (40%), Anforderungserfüllung (30%), '
                            'Klarheit (20%) und Laufzeit (10%). Keine Ausführung behaupten. JSON: winner, reason, '
                            'scores (Proben-ID -> 0..100).\nAUFGABE:\n' + goal + '\nPROBEN:\n' + json.dumps(blind, ensure_ascii=False))
            judge_context = max(contexts)
            instance = studio.switch(judge, judge_context)
            judged = studio.chat(instance, judge_prompt, temperatures_for(judge, 'general')[0], 1536)
            verdict = parse_json(judged.get('response', ''))
            scores = verdict.get('scores')
            if judged.get('finish_reason') == 'length' or not isinstance(scores, dict):
                raise ValueError('Unvollständige Modellauswertung.')
            if any(type(value) not in (int, float) or not 0 <= value <= 100 for value in scores.values()):
                raise ValueError('Ungültige Bewertungswerte.')
            for row in report['samples']:
                if row['id'] in scores:
                    row['score'] = float(scores[row['id']])
            report['judge_verdict'] = {'winner': verdict.get('winner'), 'reason': verdict.get('reason')}
        report['groups'] = _group_stats(report['samples'])
        best = report['groups'][0]
        report['recommendation'] = {
            'model': best['model'], 'context_tokens': best['context_tokens'],
            'quantization': best['quantization'], 'quality_mean': best['quality_mean'],
            'quality_stdev': best['quality_stdev'], 'tokens_per_second': best['tokens_per_second'],
            'vram_peak_bytes': best['vram_peak_bytes'],
            'reason': (f"Gemessen auf {report['hardware'].get('processor') or report['hardware'].get('machine')}: "
                       f"Qualität {best['quality_mean']} ± {best['quality_stdev']}, "
                       f"{best['tokens_per_second'] or '—'} Tokens/s, Kontext {best['context_tokens']}."),
        }
        report['status'] = 'ready'
        report['at'] = time.time()
        _save_cache(report)
        return report
    except Exception as exc:
        report.update(status='error', error=str(exc))
        save(report)
        raise
    finally:
        try:
            studio.unload()
        except Exception as exc:
            report.update(status='error', error='Entladen am Ende fehlgeschlagen: ' + str(exc))
            save(report)
        emit('Arbeitsproben beendet.')


def recommendation_caveat(report: dict) -> str:
    if not report.get('groups'):
        return 'Noch keine Messreihe vorhanden.'
    return ('Gemessene Stichprobe für diese Hardware, Quantisierung und Aufgabe. '
            'Keine Garantie eines global besten Modells; Qualitätsstreuung beachten.')
