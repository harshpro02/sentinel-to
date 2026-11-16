import React, { useEffect, useState } from 'react';
import { formatTime } from './feeds';

const fields = { title: 'Reported impact', description: 'Details', road: 'Road', location: 'Location', updatedAt: 'Source updated', startsAt: 'Start', plannedEndAt: 'Planned end', schedule: 'Schedule', comment: 'Additional information' };
const display = (key, value) => value ? key.endsWith('At') ? formatTime(value) : String(value) : 'Not supplied';

export default function IncidentHistory({ incidentId }) {
  const [attempt, setAttempt] = useState(0);
  const [state, setState] = useState({ loading: true });
  useEffect(() => {
    const controller = new AbortController();
    let disposed = false;
    const timeout = setTimeout(() => controller.abort(), 15000);
    setState({ loading: true });
    async function load() {
      try {
        const response = await fetch(`/api/incidents/${encodeURIComponent(incidentId)}/history?limit=20`, { signal: controller.signal });
        if (response.status === 404) {
          if (!disposed) setState({ empty: true });
          return;
        }
        if (!response.ok) throw new Error('History unavailable');
        const data = await response.json();
        if (!Array.isArray(data.versions)) throw new Error('Invalid history');
        if (!disposed) setState({ data });
      } catch {
        if (!disposed) setState({ error: true });
      } finally {
        clearTimeout(timeout);
      }
    }
    load();
    return () => { disposed = true; clearTimeout(timeout); controller.abort(); };
  }, [incidentId, attempt]);

  const data = state.data;
  return <section className="incident-history" aria-labelledby="history-heading" aria-busy={Boolean(state.loading)}>
    <h4 id="history-heading">Report history</h4>
    <p>Changes observed by Sentinel. Times shown in Toronto time. These records do not establish traffic speed or road clearance.</p>
    {state.loading && <p role="status">Loading saved observations…</p>}
    {state.empty && <p role="status">No saved observations yet. Collection may not have recorded this report.</p>}
    {state.error && <div role="status"><p>Saved history is temporarily unavailable. The current report remains available above.</p><button className="load-more" onClick={() => setAttempt(attempt + 1)}>Retry history</button></div>}
    {data && <>
      {data.assessment && <div className={`wait-reroute wait-reroute-${data.assessment.status}`} aria-label="Official report change assessment">
        <div className="wait-reroute-head">
          <span className="wait-reroute-status">{({ increased: 'Reported impact increased', reduced: 'Reported impact reduced', unchanged: 'Reported impact unchanged', unknown: 'Report change unknown' })[data.assessment.status]}</span>
          <span className="wait-reroute-confidence">{({ none: 'Insufficient evidence', low: 'Unvalidated comparison' })[data.assessment.confidence]}</span>
        </div>
        <p className="wait-reroute-advice">{data.assessment.advice}</p>
        <p className="wait-reroute-basis">{data.assessment.basis}</p>
        <p className="wait-reroute-note">{data.assessment.note}</p>
      </div>}
      <dl className="history-summary"><div><dt>First observed</dt><dd>{formatTime(data.firstSeenAt)}</dd></div><div><dt>Last observed in feed</dt><dd>{formatTime(data.lastSeenAt)}</dd></div></dl>
      <ol className="history-list">{data.versions.map((version, index) => {
        const older = data.versions[index + 1];
        const initial = version.observedAt === data.firstSeenAt;
        const changed = older ? Object.keys(fields).filter((key) => (version.report[key] ?? '') !== (older.report[key] ?? '')) : [];
        return <li key={version.observedAt}>
          <time dateTime={version.observedAt}>{formatTime(version.observedAt)}</time>
          <strong>{initial ? 'First saved observation' : older ? 'Report updated' : 'Saved report version'}</strong>
          {older && changed.length > 0 ? <dl className="history-changes">{changed.map((key) => <div key={key}><dt>{fields[key]}</dt><dd><span className="history-previous">Previously: {display(key, older.report[key])}</span><span>Now: {display(key, version.report[key])}</span></dd></div>)}</dl> : <p>{version.report.title}{version.report.description && ` · ${version.report.description}`}</p>}
          {older && !changed.length && <p>Other report metadata changed.</p>}
        </li>;
      })}</ol>
      {!data.versions.length && <p>No saved versions are available.</p>}
      {data.versions.length >= data.limit && <p>Showing the latest {data.versions.length} saved versions. Earlier observations may exist.</p>}
      {data.versions.length === 1 && <p>One version saved. No changes are available to compare.</p>}
    </>}
  </section>;
}
