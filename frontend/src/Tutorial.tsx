import BrandMark from './BrandMark';
import { useEffect, useLayoutEffect, useState } from 'react';
import type { CSSProperties } from 'react';
import { useI18n } from './i18n';

export type TourMode = 'main' | 'pilot' | 'collaboration' | 'developer';

type Step = { selector?: string; title: [string, string]; text: [string, string] };
const tours: Record<TourMode, Step[]> = {
  main: [
    { selector: '[data-tour="nav-projects"]', title: ['Projekte', 'Projects'], text: ['Hier liegen alle Projekte. Die Kachelansicht eignet sich für wenige, die Listenansicht für viele Projekte. Projektgruppen sortieren den Bestand zusätzlich.', 'All projects live here. The tile view suits a few projects, the list view many. Project groups add another layer of organisation.'] },
    { selector: '[data-tour="new-project"]', title: ['Neues Projekt', 'New project'], text: ['Lege ein Projekt an und gib ihm einen Namen. Die Beschreibung ist optional und dient später als Ausgangspunkt für den Aufgabenplan.', 'Create a project and give it a name. The description is optional and later serves as the starting point for the task plan.'] },
    { selector: '[data-tour="project-toolbar"]', title: ['Ansicht & Gruppen', 'View & groups'], text: ['Wechsle zwischen Kacheln und Liste. Über Gruppen ordnest du Projekte thematisch; ein Projekt lässt sich jederzeit in eine andere Gruppe oder zurück in „Ohne Gruppe“ verschieben.', 'Switch between tiles and list. Groups organise projects by topic; a project can be moved to another group or back to “No group” at any time.'] },
    { selector: '[data-tour="pilot-open"]', title: ['Pilot öffnen', 'Open Pilot'], text: ['Im Entwicklungscockpit verbindest du einen Arbeitsordner. ToolForge liest den vorhandenen Stand ein und führt danach Aufgabenplan, Vorabcheck und Ausführung zusammen.', 'In the development cockpit you connect a working folder. ToolForge reads the existing state and then combines task plan, preflight and execution.'] },
    { selector: '[data-tour="nav-roadmap"]', title: ['Entwicklungspfad', 'Development path'], text: ['Der Entwicklungspfad zeigt die vierzehn integrierten Etappen von der Projektverwaltung bis zu OpenCode Free, mehrstufiger Übergabe und unabhängiger Prüfung.', 'The development path shows the fourteen integrated stages from project management to OpenCode Free, multi-model handoff and independent review.'] },
    { selector: '[data-tour="nav-help"]', title: ['Hilfe', 'Help'], text: ['Die Hilfe enthält Bedienungsdokumente, einen dokumentgestützten Hilfechat und alle Tutorials. Jedes Tutorial lässt sich hier jederzeit erneut starten.', 'Help contains user documents, a document-based help chat and all tutorials. Every tutorial can be restarted here at any time.'] },
    { selector: '[data-tour="topbar-actions"]', title: ['Sprache, Ton & Design', 'Language, sound & theme'], text: ['Neben dem Designwechsel liegen der Hinweiston und der Sprachumschalter EN | DE. Fahre mit der Maus über das Lautsprechersymbol, um die Lautstärke einzustellen.', 'Next to the theme switch are the notification sound and the EN | DE language toggle. Hover over the speaker icon to adjust the volume.'] },
    { selector: '[data-tour="shutdown"]', title: ['Sauber beenden', 'Quit cleanly'], text: ['ToolForge beenden stoppt laufende Aufträge und den Server. Ein von ToolForge geöffnetes Chrome-/Edge-App-Fenster wird dabei automatisch geschlossen.', 'Quitting ToolForge stops running tasks and the server. A Chrome/Edge app window opened by ToolForge is closed automatically.'] }
  ],
  pilot: [
    { selector: '[data-tour="pilot-tabs"]', title: ['Die Cockpit-Bereiche', 'Cockpit areas'], text: ['Die Tabs führen durch Übersicht, Übergabe & Prüfung, Entwicklungsbereich, Aufgabenplan, Analyse & Betrieb, Protokoll und Einstellungen. Der aktive Tab bleibt beim Wechsel des Projekts erhalten.', 'The tabs guide you through overview, handoff & review, development area, task plan, analysis & operations, log and settings. The active tab is kept when switching projects.'] },
    { selector: '[data-tour="pilot-dashboard"]', title: ['Übersicht', 'Overview'], text: ['Hier siehst du geprüften Fortschritt, geschätzte weitere Durchläufe, Projektbestand, offene Rückfragen und die Arbeitspakete mit Ersteller und Prüfstatus.', 'See verified progress, estimated further runs, project inventory, open questions and work packages with creator and review status.'] },
    { selector: '[data-tour="pilot-tab-plan"]', title: ['Aufgabenplan', 'Task plan'], text: ['Beschreibe das Ziel, erstelle einen versionierten Plan und prüfe Änderungen vor der Übernahme. Der Plan bleibt auch nach einer automatischen Neuplanung nachvollziehbar.', 'Describe the goal, create a versioned plan and review changes before applying them. The plan remains traceable even after automatic replanning.'] },
    { selector: '[data-tour="preflight-panel"]', title: ['Modell-Vorabcheck', 'Model preflight'], text: ['Wähle Kandidaten und ein Auswertungsmodell, vergleiche Arbeitsproben und übernimm eine gemessene Empfehlung. Der Vorabcheck ist optional und kann übersprungen werden.', 'Choose candidates and an evaluation model, compare work samples and apply a measured recommendation. The preflight is optional and can be skipped.'] },
    { selector: '[data-tour="pilot-tab-settings"]', title: ['Einstellungen & Modellquellen', 'Settings & model sources'], text: ['Lege Quellen-Vorauswahl, Fallback-Reihenfolge und Modelle pro Quelle fest. Free-Modelle teilen sich ein Tageskontingent; lokale und bezahlte API-Quellen bleiben getrennt.', 'Set the source preset, fallback order and per-source models. Free models share one daily quota; local and paid API sources remain separate.'] },
    { selector: '[data-tour="pilot-tab-advanced"]', title: ['Analyse & Betrieb', 'Analysis & operations'], text: ['Projektanalyse, Aufgaben-Graph, Messreihen, Anwendungsabnahme, Recherche mit Textbelegen, Umgebungssperre und Docker-Sandbox sind hier gebündelt.', 'Project analysis, task graph, benchmarks, application acceptance, research with text evidence, environment lock and Docker sandbox are bundled here.'] },
    { selector: '[data-tour="pilot-tab-logs"]', title: ['Protokoll', 'Log'], text: ['Das Live-Protokoll zeigt Ausgaben der aktuellen Sitzung. Frühere Läufe liegen im verlinkten Protokollordner und bleiben für die Fehlersuche erhalten.', 'The live log shows output from the current session. Earlier runs are in the linked log folder and remain available for troubleshooting.'] },
    { selector: '[data-tour="pilot-tab-collaboration"]', title: ['Übergabe & Prüfung', 'Handoff & review'], text: ['Hier konfigurierst du, welches Modell bei Stillstand übernimmt und welche Modelle Ergebnisse unabhängig prüfen. Beide Listen sind auch während eines Laufs änderbar.', 'Here you configure which model takes over when work stalls and which models review results independently. Both lists can be changed during a run.'] },
    { selector: '[data-tour="pilot-tab-develop"]', title: ['Entwicklungsbereich', 'Development area'], text: ['Dateien, Editor, kontrollierte KI-Änderungen, Python-Ausführung, Git und visuelle Workflows stehen im Entwicklungsbereich bereit.', 'Files, editor, controlled AI changes, Python execution, Git and visual workflows are available in the development area.'] }
  ],
  collaboration: [
    { selector: '[data-tour="pilot-tab-collaboration"]', title: ['Übergabe & Prüfung öffnen', 'Open handoff & review'], text: ['Der Tab „Übergabe & Prüfung“ bündelt die Modelle, die bei Stillstand übernehmen, und die unabhängigen Prüfer. Änderungen gelten ab dem nächsten Auftrag.', 'The “Handoff & review” tab bundles the models that take over when work stalls and the independent reviewers. Changes apply from the next task.'] },
    { selector: '[data-tour="collaboration-panel"]', title: ['Zwei Rollen', 'Two roles'], text: ['Übergabemodelle werden der Reihe nach versucht, wenn das Hauptmodell nicht weiterkommt. Prüfer bewerten bestandene Aufgaben; Ersteller einer Aufgabe sind von deren Prüfung ausgeschlossen.', 'Handoff models are tried in order when the primary model gets stuck. Reviewers assess passed tasks; a task’s creator is excluded from reviewing it.'] },
    { selector: '[data-tour="collaboration-roles"]', title: ['Reihenfolge ändern', 'Change the order'], text: ['Füge Modelle hinzu, entferne sie mit „Entfernen“ und verschiebe sie mit den Pfeilen. Die gespeicherte Reihenfolge bleibt auch erhalten, wenn du später die Quellen-Vorauswahl wechselst.', 'Add models, remove them with “Remove” and move them with the arrows. The saved order survives a later change of the source preset.'] },
    { selector: '[data-tour="collaboration-save"]', title: ['Im Lauf speichern', 'Save during a run'], text: ['„Zusammenarbeit speichern“ schreibt die Auswahl in die Laufzeiteinstellungen. Das Hauptmodell bleibt ausgeschlossen; bei erschöpftem Free-Kontingent hält die Übergabe mit einem Hinweis an.', '“Save collaboration” writes the selection to the runtime settings. The primary model remains excluded; when the free quota is exhausted, handoff stops with an explanation.'] },
    { selector: '[data-tour="preflight-panel"]', title: ['Im Vorabcheck festlegen', 'Configure in preflight'], text: ['Im Vorabcheck lassen sich Übergabe- und Prüferlisten ebenfalls festlegen. Sie werden zusammen mit der Empfehlung übernommen; eine spätere Änderung erfordert einen erneuten Lauf.', 'Handoff and reviewer lists can also be set in the preflight. They are applied together with the recommendation; a later change requires another run.'] },
    { selector: '[data-tour="dashboard-tasks"]', title: ['Ergebnis prüfen', 'Check results'], text: ['In den Arbeitspaketen siehst du Ersteller und Prüfstatus. Eine eindeutige Ablehnung führt bei aktivierter Option zu einer Reparatur statt nur zu einem Protokolleintrag.', 'Work packages show creator and review status. With the option enabled, a clear rejection triggers a repair instead of only a log entry.'] },
    { selector: '[data-tour="model-sources"]', title: ['Quellen und Kontingent', 'Sources and quota'], text: ['Übergabe und Prüfung nutzen nur Modelle aus den erlaubten Quellen. Ein anderes Free-Modell schafft kein neues Kontingent; lokale und bezahlte API-Quellen bleiben eigenständig.', 'Handoff and review use only models from allowed sources. Another free model does not create new quota; local and paid API sources remain independent.'] }
  ],
  developer: [
    { selector: '[data-tour="dev-tabs"]', title: ['Entwicklungsbereich', 'Development area'], text: ['Die Tabs führen in dieser Reihenfolge durch den Arbeitsablauf: Verbesserungen, Dateien & Editor, KI-Änderungen, Ausführen & Prüfen, Git und Workflows.', 'The tabs guide you through the workflow in this order: improvements, files & editor, AI changes, run & check, Git and workflows.'] },
    { selector: '[data-tour="dev-tab-improvements"]', title: ['Verbesserungen', 'Improvements'], text: ['Auch nach dem ersten Lauf kannst du Erweiterungen einreichen oder KI-Vorschläge anfordern. Bestehende Aufgaben und Prüfnachweise bleiben erhalten.', 'Even after the first run you can submit extensions or request AI suggestions. Existing tasks and verification evidence are preserved.'] },
    { selector: '[data-tour="dev-tab-editor"]', title: ['Dateien & Editor', 'Files & editor'], text: ['Dateibaum und Codeeditor arbeiten mit Versionsprüfung und Sicherungen. Ungespeicherte Entwürfe überstehen einen versehentlichen Tab-Wechsel.', 'File tree and code editor use revision checks and backups. Unsaved drafts survive an accidental tab switch.'] },
    { selector: '[data-tour="dev-tab-ai"]', title: ['KI-Änderungen', 'AI changes'], text: ['Eine einzelne Datei ändern lassen, den Diff prüfen und den Vorschlag ausdrücklich übernehmen. Das ist getrennt vom automatischen Aufgabenplan.', 'Have a single file changed, review the diff and apply the proposal explicitly. This is separate from the automatic task plan.'] },
    { selector: '[data-tour="dev-tab-run"]', title: ['Ausführen & Prüfen', 'Run & check'], text: ['Projektumgebung anlegen, Python starten, Tests, Linting und Typprüfung ausführen. Die Live-Ausgabe und der Abbruch bleiben unter dem aktiven Tab sichtbar.', 'Create the project environment, start Python, run tests, linting and type checks. Live output and cancellation remain visible below the active tab.'] },
    { selector: '[data-tour="dev-tab-git"]', title: ['Git', 'Git'], text: ['Status, Diff und Historie prüfen. Commits benötigen eine ausdrückliche Dateiauswahl und erfassen keine ungewollt vorgemerkten Dateien.', 'Review status, diff and history. Commits require an explicit file selection and do not include unintended staged files.'] },
    { selector: '[data-tour="dev-tab-workflow"]', title: ['Workflows', 'Workflows'], text: ['Visuelle Knoten verbinden, konfigurieren und speichern. Python-, CSV-, Validierungs-, Duplikat- und Excel-Knoten teilen sich definierte Ein- und Ausgaben.', 'Connect, configure and save visual nodes. Python, CSV, validation, duplicate and Excel nodes share defined inputs and outputs.'] },
    { selector: '[data-tour="dev-output"]', title: ['Live-Ausgabe', 'Live output'], text: ['Aufträge protokollieren hier und im Projektordner. Bei Problemen zeigt die Ausgabe den konkreten Grund; Abbruch beendet nur den aktuellen Auftrag.', 'Jobs are logged here and in the project folder. On problems the output shows the concrete reason; cancellation stops only the current job.'] }
  ]
};

function bounds(selector?: string) {
  if (!selector) return null;
  const element = document.querySelector(selector);
  if (!element) return null;
  return element.getBoundingClientRect();
}

export default function Tutorial({ mode, onClose }: { mode: TourMode; onClose: () => void }) {
  const { t } = useI18n();
  const steps = tours[mode];
  const [index, setIndex] = useState(0);
  const [rect, setRect] = useState<DOMRect | null>(null);
  const step = steps[index];
  useEffect(() => { const handler = (event: KeyboardEvent) => { if (event.key === 'Escape') onClose(); }; window.addEventListener('keydown', handler); return () => window.removeEventListener('keydown', handler); }, [onClose]);
  useLayoutEffect(() => {
    let frame = 0;
    const target = step.selector ? document.querySelector<HTMLElement>(step.selector) : null;
    target?.scrollIntoView({ block: 'center', inline: 'nearest', behavior: 'smooth' });
    const update = () => { cancelAnimationFrame(frame); frame = requestAnimationFrame(() => setRect(bounds(step.selector))); };
    update();
    const delayed = window.setTimeout(update, 350);
    window.addEventListener('resize', update); window.addEventListener('scroll', update, true);
    return () => { window.clearTimeout(delayed); window.removeEventListener('resize', update); window.removeEventListener('scroll', update, true); cancelAnimationFrame(frame); };
  }, [index, step.selector]);
  const last = index === steps.length - 1;
  const viewport = { width: window.innerWidth, height: window.innerHeight };
  const cardWidth = Math.min(360, viewport.width - 28);
  let cardStyle: CSSProperties = { left: Math.max(14, (viewport.width - cardWidth) / 2), bottom: 24 };
  if (rect) {
    const below = rect.bottom + 18;
    const above = rect.top - 18 - 220;
    const top = below + 230 < viewport.height ? below : above > 16 ? above : Math.max(16, viewport.height / 2 - 110);
    cardStyle = { left: Math.max(14, Math.min(viewport.width - cardWidth - 14, rect.left + rect.width / 2 - cardWidth / 2)), top, width: cardWidth };
  }
  return <div className="tour-layer">
    <div className="tour-blocker" aria-hidden="true" />
    {rect ? <div className="tour-spotlight" aria-hidden="true" style={{ top: Math.max(4, rect.top - 6), left: Math.max(4, rect.left - 6), width: rect.width + 12, height: rect.height + 12 }} /> : <div className="tour-dim" aria-hidden="true" />}
    <button className="tour-abort" onClick={onClose}>✕ {t('Tutorial abbrechen', 'Cancel tutorial')}</button>
    <section className="tour-card" role="dialog" aria-modal="true" aria-labelledby="tour-title" style={cardStyle}>
      <div className="tour-top"><span className="tour-count">{t('Tutorial', 'Tutorial')} {index + 1} / {steps.length}</span><button className="text-button" onClick={onClose}>{t('Tutorial beenden', 'End tutorial')}</button></div>
      <h2 id="tour-title">{t(...step.title)}</h2>
      <p>{t(...step.text)}</p>
      <div className="tour-actions">
        <button className="button secondary" disabled={index === 0} onClick={() => setIndex(index - 1)}>{t('Zurück', 'Back')}</button>
        <button className="button primary" onClick={() => last ? onClose() : setIndex(index + 1)}>{last ? t('Tutorial abschließen', 'Finish tutorial') : t('Weiter', 'Next')}</button>
      </div>
    </section>
  </div>;
}

export function TutorialWelcome({ onStart, onSkip }: { onStart: () => void; onSkip: () => void }) {
  const { t } = useI18n();
  return <div className="tour-layer welcome-layer">
    <div className="tour-dim" aria-hidden="true" />
    <section className="tour-card welcome-card" role="dialog" aria-modal="true" aria-labelledby="welcome-title">
      <BrandMark className="welcome-mark" />
      <span className="eyebrow">{t('WILLKOMMEN BEI TOOLFORGE', 'WELCOME TO TOOLFORGE')}</span>
      <h2 id="welcome-title">{t('In wenigen Schritten zur eigenen Workbench.', 'Your own workbench in a few steps.')}</h2>
      <p>{t('Das kurze UI-Tutorial zeigt dir Projekte, Gruppen, Ansichten, den Pilot, den Entwicklungspfad, die Hilfe und das saubere Beenden. Weitere Tutorials für Cockpit, Übergabe & Prüfung und den Entwicklungsbereich erreichst du jederzeit über die Hilfe.', 'The short UI tutorial shows projects, groups, views, the Pilot, the development path, help and clean shutdown. Further tutorials for the cockpit, handoff & review and the development area are always available via Help.')}</p>
      <div className="tour-actions"><button className="button secondary" onClick={onSkip}>{t('Später', 'Later')}</button><button className="button primary" onClick={onStart}>{t('Tutorial starten', 'Start tutorial')}</button></div>
    </section>
  </div>;
}
