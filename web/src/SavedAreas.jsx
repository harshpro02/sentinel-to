import React, { useState } from 'react';
import { distanceKm, formatTime, useFeed } from './feeds';

const storageKey = 'sentinel.saved-areas.v1';
const roadKey = (road) => road.trim().toLowerCase().replace(/\s+/g, ' ');

export function reportsFor(area, items) {
  return items.filter((item) => {
    if (!['incident', 'construction'].includes(item.type)) return false;
    if (area.kind === 'place') return distanceKm(area.coordinates, item.coordinates) <= 5;
    const [lon, lat] = item.coordinates;
    const [west, south, east, north] = area.bounds;
    return lon >= west && lon <= east && lat >= south && lat <= north && roadKey(item.road) === roadKey(area.road);
  });
}

export default function SavedAreas({ active, region }) {
  const [areas, setAreas] = useState(() => {
    try {
      const saved = JSON.parse(localStorage.getItem(storageKey) ?? '[]');
      return Array.isArray(saved) ? saved : [];
    } catch { return []; }
  });
  const [selected, setSelected] = useState(null);
  const [status, setStatus] = useState('');
  const area = areas.find((entry) => entry.id === selected);
  const feed = useFeed(area ? '/api/incidents' : null);
  const reports = area ? reportsFor(area, feed.items) : [];

  function save(next) {
    try {
      localStorage.setItem(storageKey, JSON.stringify(next));
      setAreas(next);
      return true;
    } catch {
      setStatus('This browser could not update saved areas.');
      return false;
    }
  }

  function add(kind) {
    const id = kind === 'place' ? JSON.stringify([kind, active.coordinates]) : JSON.stringify([kind, roadKey(active.road), region.bounds]);
    if (areas.some((entry) => entry.id === id)) {
      setSelected(id);
      setStatus('Already saved.');
      return;
    }
    if (areas.length >= 30) {
      setStatus('Remove a saved area before adding another.');
      return;
    }
    const entry = kind === 'place'
      ? { id, kind, label: active.location || active.road, coordinates: active.coordinates }
      : { id, kind, label: `${active.road} · ${region.label}`, road: active.road, bounds: region.bounds };
    if (save([...areas, entry])) {
      setSelected(id);
      setStatus('Saved on this browser.');
    }
  }

  return <section className="saved-areas" aria-label="Saved areas">
    <h2>Saved areas</h2>
    <p>Save a selected place or road to check official reports before leaving.</p>
    {active && <div className="saved-actions">
      <button type="button" onClick={() => add('place')}>Save place</button>
      {['incident', 'construction'].includes(active.type) && active.road?.trim() && <button type="button" onClick={() => add('corridor')}>Save road in this region</button>}
    </div>}
    {areas.length > 0 && <div className="saved-actions">
      <select aria-label="Saved area" value={selected ?? ''} onChange={(event) => { setSelected(event.target.value || null); setStatus(''); }}>
        <option value="">Choose a saved area</option>
        {areas.map((entry) => <option key={entry.id} value={entry.id}>{entry.label}</option>)}
      </select>
      {area && <button type="button" onClick={() => {
        if (save(areas.filter((entry) => entry.id !== area.id))) {
          setSelected(null);
          setStatus('Saved area removed.');
        }
      }}>Remove</button>}
    </div>}
    <div role="status">{status}</div>
    {area && <section aria-label="Relevant official reports">
      <p>{area.kind === 'place' ? 'Official reports within 5 km.' : 'Reports with the same official road name inside the saved region.'}</p>
      {feed.loading && <p role="status">Checking official reports…</p>}
      {(feed.stale || feed.error) && <p role="status">The official feed may be out of date.</p>}
      {feed.fetchedAt && <p>Retrieved {formatTime(feed.fetchedAt)}</p>}
      {!feed.loading && !feed.error && !feed.stale && reports.length === 0 && <p>No matching official reports were found.</p>}
      {reports.length > 0 && <ul>{reports.map((report) => <li key={report.id}><strong>{report.title}</strong><span>{report.road} · {report.location}</span>{report.startsAt && <span>Reported start {formatTime(report.startsAt)}</span>}</li>)}</ul>}
    </section>}
  </section>;
}
