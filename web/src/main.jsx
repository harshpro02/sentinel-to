import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { createRoot } from 'react-dom/client';
import { ArrowLeft, ArrowUpRight, ChevronRight, Compass, Construction, Eye, Layers, MapPin, Search, Shield, TriangleAlert, X } from 'lucide-react';
import OntarioMap, { regions } from './OntarioMap';
import CameraViewer from './CameraViewer';
import { distanceKm, formatTime, useFeed } from './feeds';
import './styles.css';

function App() {
  const [query, setQuery] = useState('');
  const [layers, setLayers] = useState({ incident: true, construction: true, camera: false });
  const [tab, setTab] = useState('incidents');
  const [selectedId, setSelectedId] = useState(null);
  const [tilted, setTilted] = useState(false);
  const [region, setRegion] = useState('gta');
  const [resetCount, setResetCount] = useState(0);
  const [showLayers, setShowLayers] = useState(false);
  const [limit, setLimit] = useState(30);
  const box = regions[region].bounds.join(',');
  const events = useFeed(`/api/incidents?bbox=${box}`);
  const cameras = useFeed(`/api/cameras?bbox=${box}`);
  const detailsHeading = useRef(null);
  const previousCard = useRef(null);
  const all = useMemo(() => [...events.items, ...cameras.items], [events.items, cameras.items]);
  const matches = useCallback((item) => `${item.road} ${item.location} ${item.description ?? ''} ${item.provider ?? ''}`.toLowerCase().includes(query.trim().toLowerCase()), [query]);
  const mapItems = useMemo(() => all.filter((item) => layers[item.type] && matches(item)), [all, layers, matches]);
  const listItems = useMemo(() => mapItems.filter((item) => tab === 'cameras' ? item.type === 'camera' : item.type !== 'camera'), [mapItems, tab]);
  const active = mapItems.find((item) => item.id === selectedId);
  const feed = active?.type === 'camera' || tab === 'cameras' ? cameras : events;
  const nearby = useMemo(() => active && active.type !== 'camera' ? cameras.items.map((camera) => ({ ...camera, distance: distanceKm(active.coordinates, camera.coordinates) })).filter((camera) => camera.distance <= 5).sort((a, b) => a.distance - b.distance).slice(0, 4) : [], [active, cameras.items]);

  const selectIncident = useCallback((item) => {
    previousCard.current = document.activeElement;
    setSelectedId(item.id);
  }, []);
  function closeDetails() {
    setSelectedId(null);
    previousCard.current?.focus();
  }
  function changeTab(next) {
    setTab(next);
    setSelectedId(null);
    setLimit(30);
    if (next === 'cameras') setLayers((previous) => ({ ...previous, camera: true }));
  }
  function openCamera(camera) {
    setQuery('');
    setTab('cameras');
    setLayers((previous) => ({ ...previous, camera: true }));
    selectIncident(camera);
  }
  useEffect(() => { if (active) detailsHeading.current?.focus(); }, [active?.id]);
  useEffect(() => {
    const close = (event) => { if (event.key === 'Escape') { setShowLayers(false); if (active) closeDetails(); } };
    window.addEventListener('keydown', close);
    return () => window.removeEventListener('keydown', close);
  }, [active]);
  useEffect(() => setLimit(30), [query, region]);

  return <div className="app">
    <a href="#activity" className="skip-link">Skip to reports</a>
    <header className="topbar">
      <a className="brand" href="/" aria-label="Sentinel home"><span className="brand-mark"><Eye size={23} /></span><span>SENTINEL<small>ONTARIO · ROAD AWARENESS</small></span></a>
      <div className="top-context">GTA & ONTARIO <span className="divider" /><a href="https://511on.ca/" target="_blank" rel="noreferrer">Data: Ontario 511</a></div>
      <span className="preview-badge">{events.loading ? 'CONNECTING TO 511' : events.stale ? 'DATA DELAYED' : 'OFFICIAL REPORTS'}</span>
    </header>
    <main className="workspace">
      <OntarioMap items={mapItems} selected={active} onSelect={selectIncident} tilted={tilted} region={region} resetCount={resetCount} />
      <div className="map-vignette" aria-hidden="true" />
      <aside className="sidebar" aria-label="Explore controls">
        <div className="panel-heading"><span className="eyebrow">ROAD REPORTS & CAMERAS</span><h1>{regions[region].label}</h1><p>Check conditions before you travel.</p></div>
        <label className="search"><Search size={18} /><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search roads or report details" aria-label="Search roads or report details" /></label>
        <label className="region-picker"><MapPin size={15} /><span>Map region</span><select aria-label="Map region" value={region} onChange={(event) => { setRegion(event.target.value); setSelectedId(null); }}>{Object.entries(regions).map(([key, value]) => <option key={key} value={key}>{value.label}</option>)}</select></label>
        <div className="feed-status" role="status"><span className={`feed-dot ${feed.stale ? 'delayed' : feed.loading ? 'pending' : ''}`} /><p>{feed.loading ? 'Fetching official data…' : feed.fetchedAt ? `Feed retrieved ${formatTime(feed.fetchedAt)}` : 'Official feed unavailable'}<small>Toronto time · individual reports have their own update times.</small></p></div>
        {feed.error && <div className="feed-warning" role="status">{feed.error}</div>}
        <div className="content-tabs" role="group" aria-label="Browse data"><button aria-pressed={tab === 'incidents'} onClick={() => changeTab('incidents')}>Road reports <span>{events.items.length}</span></button><button aria-pressed={tab === 'cameras'} onClick={() => changeTab('cameras')}>Cameras <span>{cameras.items.length}</span></button></div>
        <section id="activity" aria-labelledby="activity-title" tabIndex={-1}>
          <div className="section-title"><h2 id="activity-title">{active ? active.type === 'camera' ? 'Camera details' : 'Report details' : tab === 'cameras' ? 'Official cameras' : 'Official road reports'}</h2><span className="count">{listItems.length} shown</span></div>
          {active ? <article className="detail-card">
            <button className="back-button" onClick={closeDetails}><ArrowLeft size={15} /> Back to list</button>
            <div className={`type-label ${active.severity ?? 'camera'}`}>{active.type === 'camera' ? <Eye size={14} /> : <TriangleAlert size={14} />} {active.label}<span>ONTARIO 511</span></div>
            <h3 ref={detailsHeading} tabIndex={-1}>{active.road}</h3><p className="location">{active.location}</p>
            {active.type === 'camera' ? <><p className="description">Direction supplied: {active.direction}</p><CameraViewer key={active.id} camera={active} stale={cameras.stale} /></> : <>
              <div className="detail-impact"><span>REPORTED LANES / IMPACT</span><strong>{active.title}</strong></div>
              <p className="report-updated">Report updated: {formatTime(active.updatedAt)} (Toronto time)</p>
              {active.startsAt && new Date(active.startsAt) > new Date() && <p className="camera-warning">Scheduled to start {formatTime(active.startsAt)}. This report may describe future work.</p>}
              <p className="description">{active.description}</p>
              {active.comment && <p className="description">{active.comment}</p>}
              <div className="evidence"><Shield size={18} /><div><strong>Traffic trend unknown</strong><p>Official reports describe disruptions. Camera snapshots do not establish speed or whether a road is clearing.</p></div></div>
              <section className="nearby-cameras"><h4>Nearby official cameras</h4><p>Within 5 km · direction and road may differ.</p>{cameras.loading ? <p>Loading cameras…</p> : nearby.length ? nearby.map((camera) => <button key={camera.id} onClick={() => openCamera(camera)}><Eye size={15} /><span>{camera.road}<small>{camera.location} · {camera.distance.toFixed(1)} km</small></span><ChevronRight size={14} /></button>) : <p>{cameras.error ? 'Camera feed unavailable.' : 'No camera listed within 5 km in this region.'}</p>}</section>
              <details><summary>Source & schedule</summary><p>Ontario 511 · {active.organization}</p><p>Reported: {formatTime(active.reportedAt)}</p><p>Start: {formatTime(active.startsAt)}</p><p>Planned end: {formatTime(active.plannedEndAt)}</p>{active.schedule && <p>{active.schedule}</p>}<p>Source severity: {active.sourceSeverity}. Closure schedules may vary; consult the full official report.</p></details>
            </>}
            <a className="official-link" href="https://511on.ca/" target="_blank" rel="noreferrer">Open official Ontario 511 <ArrowUpRight size={16} /></a>
          </article> : <div className="incident-list">
            {listItems.slice(0, limit).map((item) => <button key={item.id} className="incident-card" onClick={() => selectIncident(item)}>
              <span className={`incident-icon ${item.severity ?? 'camera'}`}>{item.type === 'camera' ? <Eye size={19} /> : item.type === 'construction' ? <Construction size={19} /> : <TriangleAlert size={19} />}</span>
              <span className="incident-copy"><span className="incident-meta">{item.label}<span>511</span></span><strong>{item.road}</strong><span className="location">{item.location}</span><span className="impact">{item.type === 'camera' ? `${item.views.filter((view) => view.enabled).length} image view(s) · ${item.provider}` : item.title}</span>{item.type !== 'camera' && <span className="report-time">Updated {formatTime(item.updatedAt)}</span>}</span><ChevronRight size={16} className="card-chevron" />
            </button>)}
            {listItems.length > limit && <button className="load-more" onClick={() => setLimit(limit + 30)}>Show 30 more</button>}
            {!listItems.length && <div className="empty-state"><Search size={24} /><h3>{feed.loading ? 'Loading official data' : feed.error && !feed.fetchedAt ? 'Feed unavailable' : 'No matching reports'}</h3><p>{feed.loading ? 'Connecting to Ontario 511.' : 'Try another road, region or map layer. Missing reports do not establish that a road is clear.'}</p><button onClick={() => { setQuery(''); setLayers({ incident: true, construction: true, camera: tab === 'cameras' }); }}>Reset filters</button></div>}
          </div>}
        </section>
        <footer className="panel-footer"><Shield size={14} /><span>Data from <a href="https://511on.ca/" target="_blank" rel="noreferrer">Ontario 511</a>.<br /><span className="muted">Provided as available; road conditions can differ. Use before travelling.</span></span></footer>
      </aside>
      <div className="map-toolbar">
        <div className="map-label"><span>{regions[region].label.toUpperCase()}<small>OFFICIAL ROAD REPORTS / CAMERA LOCATIONS</small></span></div>
        <div className="map-actions">
          <button className={tilted ? 'tool active' : 'tool'} onClick={() => setTilted(!tilted)} aria-pressed={tilted}><Compass size={16} /><span>{tilted ? 'Tilted view' : 'Flat view'}</span></button>
          <div className="layer-wrapper">
            <button className={showLayers ? 'tool active' : 'tool'} onClick={() => setShowLayers(!showLayers)} aria-expanded={showLayers} aria-controls="layers-panel"><Layers size={16} /><span>Layers</span></button>
            {showLayers && <section className="layers-panel" id="layers-panel" aria-label="Map layers"><div className="section-title"><h2>Map layers</h2><button className="icon-button" aria-label="Close layers" onClick={() => setShowLayers(false)}><X size={16} /></button></div><p>Choose what appears on the map.</p>{[['incident', 'Road incidents', TriangleAlert], ['construction', 'Roadwork', Construction], ['camera', 'Cameras', Eye]].map(([key, label, Icon]) => <label key={key} className="layer-option"><Icon size={17} /><span>{label}<small>Ontario 511</small></span><input type="checkbox" checked={layers[key]} onChange={(event) => setLayers({ ...layers, [key]: event.target.checked })} /></label>)}</section>}
          </div>
          <button className="tool reset-tool" aria-label="Return to the Greater Toronto Area" onClick={() => { setSelectedId(null); setRegion('gta'); setTilted(false); setResetCount(resetCount + 1); }}><MapPin size={16} /><span>GTA</span></button>
        </div>
      </div>
      <div className="map-legend"><span><i className="legend-dot high" /> Reported closure</span><span><i className="legend-dot medium" /> Roadwork</span><span><i className="legend-dot camera" /> Camera</span></div>
    </main>
  </div>;
}

createRoot(document.getElementById('root')).render(<React.StrictMode><App /></React.StrictMode>);
