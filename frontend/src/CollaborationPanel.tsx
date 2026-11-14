import { useEffect, useState } from 'react';
import type { Snapshot } from './pilotTypes';
import { useI18n } from './i18n';

export type RoleModel = {
  key: string;
  model?: string;
  name?: string;
  source?: string;
  source_label?: string;
  context?: number;
  blocked?: boolean;
};

type RequestFn = <T>(path: string, data?: unknown, method?: string) => Promise<T>;

export function RoleEditor({ label, hint, models, selected, onChange, disabled, emptyLabel }: {
  label: string;
  hint: string;
  models: RoleModel[];
  selected: string[];
  onChange: (next: string[]) => void;
  disabled: boolean;
  emptyLabel: string;
}) {
  const { t } = useI18n();
  const [candidate, setCandidate] = useState('');
  const known = new Map(models.map(model => [model.key, model]));
  const add = () => {
    if (!candidate || selected.includes(candidate)) return;
    onChange([...selected, candidate]);
    setCandidate('');
  };
  const move = (index: number, delta: number) => {
    const next = [...selected];
    const target = index + delta;
    if (target < 0 || target >= next.length) return;
    [next[index], next[target]] = [next[target], next[index]];
    onChange(next);
  };
  return <div className="role-editor">
    <div className="role-editor-head"><strong>{label}</strong><small>{hint}</small></div>
    {selected.length ? <ol className="role-list">{selected.map((key, index) => {
      const row = known.get(key);
      return <li key={key}>
        <span className="role-index">{index + 1}</span>
        <span className="role-name">{row?.source_label ? `${row.source_label} · ` : ''}{row?.name || key}{row?.blocked ? ` · ${t('gesperrt', 'blocked')}` : ''}</span>
        <button type="button" className="text-button" disabled={disabled || index === 0} title={t('Nach oben', 'Move up')} aria-label={t('Nach oben', 'Move up')} onClick={() => move(index, -1)}>↑</button>
        <button type="button" className="text-button" disabled={disabled || index === selected.length - 1} title={t('Nach unten', 'Move down')} aria-label={t('Nach unten', 'Move down')} onClick={() => move(index, 1)}>↓</button>
        <button type="button" className="text-button danger-text" disabled={disabled} onClick={() => onChange(selected.filter(item => item !== key))}>{t('Entfernen', 'Remove')}</button>
      </li>;
    })}</ol> : <p className="role-empty">{emptyLabel}</p>}
    <div className="role-add">
      <select aria-label={t('Modell hinzufügen', 'Add model')} value={candidate} disabled={disabled} onChange={event => setCandidate(event.target.value)}>
        <option value="">{t('Modell auswählen …', 'Choose a model …')}</option>
        {models.filter(model => !selected.includes(model.key)).map(model => <option value={model.key} key={model.key}>
          {model.source_label ? model.source_label + ' · ' : ''}{model.name || model.key}{model.blocked ? ` · ${t('gesperrt', 'blocked')}` : ''}
        </option>)}
      </select>
      <button type="button" className="button secondary" disabled={disabled || !candidate} onClick={add}>{t('Hinzufügen', 'Add')}</button>
    </div>
  </div>;
}

export default function CollaborationPanel({ base, snapshot, request, refresh, compact = false }: {
  base: string;
  snapshot: Snapshot;
  request: RequestFn;
  refresh: () => Promise<void>;
  compact?: boolean;
}) {
  const { t } = useI18n();
  const [inventory, setInventory] = useState<{ models: RoleModel[]; handoff_models: string[]; review_models: string[]; settings: Record<string, unknown>; blocked_message?: string; errors?: Record<string, string> } | null>(null);
  const [handoff, setHandoff] = useState<string[]>([]);
  const [review, setReview] = useState<string[]>([]);
  const [handoffEnabled, setHandoffEnabled] = useState(Boolean(snapshot.settings.handoff_enabled));
  const [reviewEnabled, setReviewEnabled] = useState(Boolean(snapshot.settings.review_enabled));
  const [strict, setStrict] = useState(snapshot.settings.review_strict !== false);
  const [afterFailures, setAfterFailures] = useState(Number(snapshot.settings.handoff_after_failures ?? 2));
  const [minApprovals, setMinApprovals] = useState(Number(snapshot.settings.review_min_approvals ?? 1));
  const [pending, setPending] = useState(false);
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');

  async function load() {
    try {
      const data = await request<typeof inventory>(base + '/collaboration/models');
      setInventory(data);
      setHandoff(data?.handoff_models || []);
      setReview(data?.review_models || []);
      const settings = data?.settings || {};
      setHandoffEnabled(Boolean(settings.handoff_enabled ?? snapshot.settings.handoff_enabled));
      setReviewEnabled(Boolean(settings.review_enabled ?? snapshot.settings.review_enabled));
      setStrict(Boolean(settings.review_strict ?? snapshot.settings.review_strict));
      setAfterFailures(Number(settings.handoff_after_failures ?? snapshot.settings.handoff_after_failures ?? 2));
      setMinApprovals(Number(settings.review_min_approvals ?? snapshot.settings.review_min_approvals ?? 1));
    } catch (err) {
      setError((err as Error).message);
    }
  }
  useEffect(() => { void load(); }, [snapshot.settings.source_mode, snapshot.settings.preference, snapshot.folder]);

  async function save() {
    setPending(true); setError(''); setMessage('');
    try {
      const result = await request<Snapshot>(base + '/runtime/options', {
        handoff_models: handoff, review_models: review,
        handoff_enabled: handoffEnabled, review_enabled: reviewEnabled,
        review_strict: strict, handoff_after_failures: afterFailures,
        review_min_approvals: minApprovals
      });
      setMessage(t('Zusammenarbeit gespeichert. Änderungen gelten ab dem nächsten Auftrag.', 'Collaboration saved. Changes apply from the next task.'));
      void result;
      await load();
      await refresh();
    } catch (err) {
      setError((err as Error).message);
    } finally { setPending(false); }
  }

  const models = inventory?.models || [];
  const modelChoices = models.map(model => ({ ...model, name: model.name || model.model }));
  return <section className={`panel collaboration-panel${compact ? ' compact' : ''}`} data-tour="collaboration-panel">
    <div className="panel-title"><div><h2>{t('Übergabe & unabhängige Prüfung', 'Handoff & independent review')}</h2><p>{t('Wenn ein Modell nicht weiterkommt, übernimmt das nächste Modell aus der Übergabeliste. Nach bestandenen Prüfungen bewerten andere Modelle das Ergebnis. Die Reihenfolge ist frei wählbar und gilt auch für laufende Aufträge.', 'When a model gets stuck, the next model in the handoff list takes over. After checks pass, other models review the result. You can reorder both lists at any time, including during a run.')}</p></div><span className="stage-badge">{t('änderbar im Lauf', 'editable while running')}</span></div>
    <div className="collaboration-options">
      <label className="check-label"><input type="checkbox" checked={handoffEnabled} disabled={pending} onChange={event => setHandoffEnabled(event.target.checked)} />{t('Übergabe an andere Modelle erlauben', 'Allow handoff to other models')}</label>
      <label className="check-label"><input type="checkbox" checked={reviewEnabled} disabled={pending} onChange={event => setReviewEnabled(event.target.checked)} />{t('Unabhängige Ergebnisprüfung erlauben', 'Allow independent result review')}</label>
      <label className="check-label"><input type="checkbox" checked={strict} disabled={pending} onChange={event => setStrict(event.target.checked)} />{t('Bei eindeutiger Ablehnung reparieren statt nur protokollieren', 'Repair after a clear rejection instead of only logging it')}</label>
      <label className="field compact-field">{t('Übergabe nach Fehlversuchen', 'Hand off after failed attempts')}<input type="number" min={1} max={8} value={afterFailures} disabled={pending} onChange={event => setAfterFailures(Number(event.target.value))} /></label>
      <label className="field compact-field">{t('Mindestzustimmungen für Prüfung', 'Minimum review approvals')}<input type="number" min={1} max={8} value={minApprovals} disabled={pending} onChange={event => setMinApprovals(Number(event.target.value))} /></label>
    </div>
    <div className="role-grid" data-tour="collaboration-roles">
      <RoleEditor label={t('Übergabe-Reihenfolge', 'Handoff order')} hint={t('Wird der Reihe nach versucht; das aktive Hauptmodell bleibt ausgeschlossen.', 'Tried in order; the active primary model is excluded.')} models={modelChoices} selected={handoff} onChange={setHandoff} disabled={pending || !handoffEnabled} emptyLabel={t('Keine Übergabemodelle gewählt. Das Hauptmodell bleibt allein zuständig.', 'No handoff models selected. The primary model remains solely responsible.')} />
      <RoleEditor label={t('Prüfer-Reihenfolge', 'Reviewer order')} hint={t('Ersteller einer Aufgabe werden automatisch von deren Prüfung ausgeschlossen.', 'Creators of a task are automatically excluded from reviewing it.')} models={modelChoices} selected={review} onChange={setReview} disabled={pending || !reviewEnabled} emptyLabel={t('Keine Prüfer gewählt. Es findet keine unabhängige Prüfung statt.', 'No reviewers selected. No independent review will run.')} />
    </div>
    {inventory?.blocked_message && <p className="field-hint">{inventory.blocked_message}</p>}
    {!!inventory?.errors && Object.keys(inventory.errors).length > 0 && <p className="field-hint">{Object.entries(inventory.errors).map(([source, text]) => `${source}: ${text}`).join(' · ')}</p>}
    <div className="inline-actions" data-tour="collaboration-save"><button type="button" className="button primary" disabled={pending} onClick={() => void save()}>{t('Zusammenarbeit speichern', 'Save collaboration')}</button><button type="button" className="button secondary" disabled={pending} onClick={() => void load()}>{t('Modellliste aktualisieren', 'Refresh model list')}</button></div>
    {message && <p className="notice" role="status">✓ {message}</p>}
    {error && <p className="field-error" role="alert">{error}</p>}
    <p className="field-hint">{t('Hinweis: Free-Modelle teilen sich ein Tageskontingent. Ein anderes Free-Modell gewinnt dadurch kein neues Kontingent; die Übergabe hält bei Erschöpfung mit einem Hinweis an.', 'Note: free models share one daily quota. A different free model does not create new quota; handoff stops with an explanation when the quota is exhausted.')}</p>
  </section>;
}
