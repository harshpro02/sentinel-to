import React, { useEffect, useMemo, useRef, useState } from 'react';
import { createRoot } from 'react-dom/client';
import { ArrowLeft, ArrowRight, ArrowUpRight, BusFront, ChevronDown, CloudSnow, Coffee, Construction, Eye, Fuel, Info, MapPin, ParkingCircle, Route, Search, Ship, TriangleAlert, Truck } from 'lucide-react';
import OntarioMap, { regions } from './OntarioMap';
import CameraViewer from './CameraViewer';
import { distanceKm, formatTime, useFeed } from './feeds';
import { categories, categoryMatches, itemMatches } from './categories';
import './styles.css';

const icons = { alert: TriangleAlert, camera: Eye, weather: CloudSnow, transit: BusFront, rest: Coffee, fuel: Fuel, construction: Construction, parking: ParkingCircle, ferry: Ship, info: Info, route: Route, truck: Truck };
const iconFor = (item) => icons[categories.find((category) => category.id === (item.type === 'incident' ? 'events' : item.type === 'camera' ? 'cameras' : item.type))?.icon] ?? MapPin;
const scheduled = (item) => item.startsAt && new Date(item.startsAt) > new Date();

function CameraThumbnail({ camera }) {
  const [failed, setFailed] = useState(false);
  const view = camera.views.find((entry) => entry.enabled);
  if (!view || failed) return <Eye size={18} />;
  return <img loading="lazy" src={`/api/cameras/${encodeURIComponent(camera.id)}/views/${encodeURIComponent(view.id)}/snapshot`} alt="" onError={() => setFailed(true)} />;
}

function ResultCard({ item, onSelect, preview }) {
  const Icon = iconFor(item);
  const isReport = item.type === 'incident' || item.type === 'construction';
  return <button className="explore-card" onClick={() => onSelect(item)}>
    <span className={preview && item.type === 'camera' ? 'camera-thumbnail' : `place-icon ${item.type === 'incident' ? 'coral' : item.type === 'construction' ? 'amber' : 'mint'}`}>{preview && item.type === 'camera' ? <CameraThumbnail key={item.id} camera={item} /> : <Icon size={18} />}</span>
    <span className="place-copy"><span className="place-kind">{scheduled(item) ? 'Scheduled work' : item.label}</span><strong>{isReport ? item.title : item.road}</strong><span className="place-location">{isReport ? `${item.road} · ${item.location}` : item.location}</span>{!isReport && item.title && item.title !== item.location && <span className="place-summary">{item.title}</span>}{item.conditionUnknown && <span className="source-warning">Current conditions unknown · source updated {formatTime(item.updatedAt)}</span>}<span className="place-action">{item.type === 'camera' ? 'See road snapshot' : isReport ? 'See what’s affected' : 'Explore this place'}<ArrowRight size={12} /></span></span>
  </button>;
}

function App() {
  const [query, setQuery] = useState('');
  const [category, setCategory] = useState('explore');
  const [expanded, setExpanded] = useState(false);
  const [selectedId, setSelectedId] = useState(null);
  const [region, setRegion] = useState('gta');
  const [resetCount, setResetCount] = useState(0);
  const [limit, setLimit] = useState(20);
  const detailsHeading = useRef(null);
  const previousCard = useRef(null);
  const box = regions[region].bounds.join(',');
  const events = useFeed(`/api/incidents?bbox=${box}`);
  const cameras = useFeed(`/api/cameras?bbox=${box}`);
  const resource = useFeed(categories.some((entry) => entry.id === category) && !['events', 'cameras'].includes(category) ? `/api/explore/${category}?bbox=${box}` : null);
  const metadata = categories.find((entry) => entry.id === category);
  const cameraItems = useMemo(() => [...cameras.items].sort((a, b) => distanceKm(a.coordinates, regions[region].coordinates) - distanceKm(b.coordinates, regions[region].coordinates)), [cameras.items, region]);
  const feed = category === 'cameras' ? { ...cameras, items: cameraItems } : category === 'explore' || category === 'events' ? events : resource;
  const candidates = useMemo(() => category === 'events' ? feed.items.filter((item) => item.type === 'incident') : feed.items, [category, feed.items]);
  const results = useMemo(() => candidates.filter((item) => itemMatches(item, query)), [candidates, query]);
  const visibleCategories = categories.filter((entry, index) => query.trim() ? categoryMatches(entry, query) : expanded || index < 6);
  const all = [...events.items, ...cameras.items, ...resource.items];
  const active = all.find((item) => item.id === selectedId);
  const nearby = useMemo(() => active ? cameras.items.filter((camera) => camera.id !== active.id).map((camera) => ({ ...camera, distance: distanceKm(active.coordinates, camera.coordinates) })).filter((camera) => camera.distance <= 5).sort((a, b) => a.distance - b.distance).slice(0, 3) : [], [active, cameras.items]);

  function chooseCategory(next) {
    setCategory(next);
    setQuery('');
    setSelectedId(null);
    setLimit(20);
  }
  function select(item) {
    previousCard.current = document.activeElement;
    setSelectedId(item.id);
  }
  function close() {
    setSelectedId(null);
    previousCard.current?.focus();
  }
  function openCamera(camera) {
    chooseCategory('cameras');
    select(camera);
  }
  useEffect(() => { if (active) detailsHeading.current?.focus(); }, [active?.id]);
  useEffect(() => {
    const escape = (event) => { if (event.key === 'Escape' && !document.querySelector('dialog[open]')) close(); };
    window.addEventListener('keydown', escape);
    return () => window.removeEventListener('keydown', escape);
  }, []);
  useEffect(() => { setLimit(20); }, [query, region]);
  const featured = results.filter((item) => !scheduled(item)).slice(0, 4);
  const showing = category === 'explore' && !query ? featured : results.slice(0, limit);
  const mapItems = useMemo(() => active && !results.some((item) => item.id === active.id) ? [...results, active] : results, [results, active]);

  return <div className="app">
    <a href="#activity" className="skip-link">Skip to results</a>
    <header className="topbar"><a className="brand" href="/" aria-label="Sentinel home"><span className="brand-mark"><Eye size={23} /></span><span>SENTINEL<small>EXPLORE YOUR WAY</small></span></a><div className="top-context">Ontario, in view.<span className="divider" /><a href="https://511on.ca/" target="_blank" rel="noreferrer">511 + Toronto data</a></div><span className="preview-badge">GTA & ONTARIO</span></header>
    <main className="workspace">
      <OntarioMap items={mapItems} selected={active} onSelect={select} tilted={false} region={region} resetCount={resetCount} />
      <aside className="sidebar explorer" aria-label="Explore Ontario">
        <div className="explore-heading"><span className="eyebrow">GTA & BEYOND</span><h1>What’s on your way?</h1><p>Cameras, useful stops and road conditions.</p></div>
        <label className="search"><Search size={18} /><input value={query} onChange={(event) => { setQuery(event.target.value); setSelectedId(null); }} placeholder="Cameras, rest areas, Highway 401…" aria-label="Search places, categories and roads" />{query && <button className="clear-search" onClick={() => setQuery('')} aria-label="Clear search">×</button>}</label>
        <label className="region-picker"><MapPin size={14} /><span>Exploring</span><select aria-label="Map region" value={region} onChange={(event) => { setRegion(event.target.value); setSelectedId(null); }}>{Object.entries(regions).map(([key, value]) => <option key={key} value={key}>{value.label}</option>)}</select></label>
        {!active && <button className="downtown-shortcut" onClick={() => { chooseCategory('cameras'); setRegion('downtown'); }}><Eye size={19} /><span>Downtown cameras<small>Street-level views around the core</small></span><ArrowRight size={14} /></button>}
        {!active && <><div className="browse-heading"><span>{query ? 'Matching categories' : 'What are you looking for?'}</span><button aria-expanded={expanded} onClick={() => setExpanded(!expanded)}>{expanded ? 'Less' : 'All categories'}<ChevronDown size={12} /></button></div><div className="category-grid">{visibleCategories.map((entry) => { const Icon = icons[entry.icon]; return <button key={entry.id} className={category === entry.id ? 'category-button chosen' : 'category-button'} aria-pressed={category === entry.id} title={entry.hint} onClick={() => chooseCategory(entry.id)}><Icon size={18} /><span>{entry.label}</span></button>; })}</div>{category !== 'explore' && <button className="back-button explore-back" onClick={() => chooseCategory('explore')}><ArrowLeft size={13} /> Back to explore</button>}</>}
        <section id="activity" tabIndex={-1} aria-labelledby="activity-title">
          <div className="section-title explore-section"><h2 id="activity-title">{active ? active.label : category === 'explore' ? query ? 'Matching reports' : 'Worth a look' : metadata?.label}</h2>{!active && category !== 'explore' && <span className="count">{results.length} in region</span>}</div>
          {!active && metadata && <p className="category-hint">{metadata.hint}</p>}
          {active ? <article className="detail-card">
            <button className="back-button" onClick={close}><ArrowLeft size={14} /> Back to results</button><h3 ref={detailsHeading} tabIndex={-1}>{active.road}</h3><p className="location">{active.location}</p>
            {active.type === 'camera' ? <CameraViewer key={active.id} camera={active} stale={cameras.stale} nearby={nearby} onSelectCamera={openCamera} /> : <>
              <div className="detail-impact"><span>{active.type === 'incident' || active.type === 'construction' ? 'OFFICIAL REPORTED IMPACT' : 'PROVIDER INFORMATION'}</span><strong>{active.title}</strong></div>{scheduled(active) && <p className="camera-warning">Scheduled to start {formatTime(active.startsAt)}. This may describe future work.</p>}{active.conditionUnknown && <p className="camera-warning">No current condition report is available. The details below may be old; do not treat them as current road conditions.</p>}<p className="description">{active.description}</p>{active.updatedAt && <p className="report-updated">Source updated {formatTime(active.updatedAt)}</p>}
              {active.facts?.length > 0 && <dl className="place-facts">{active.facts.map((fact) => <div key={fact.label}><dt>{fact.label}</dt><dd>{fact.value}</dd></div>)}</dl>}{active.segments?.length > 0 && <p className="category-hint">Conditions apply to the highlighted road segment, not just the marker.</p>}
              {(active.type === 'incident' || active.type === 'construction') && <><section className="nearby-cameras"><h4>Take a look nearby</h4><p>Official snapshots within 5 km. Cameras may face a different road or direction.</p>{nearby.map((camera) => <button key={camera.id} onClick={() => openCamera(camera)}><Eye size={15} /><span>{camera.road}<small>{camera.distance.toFixed(1)} km · {camera.location}</small></span><ArrowRight size={13} /></button>)}{!nearby.length && <p>{cameras.error ? 'Camera information is unavailable.' : 'No cameras listed nearby.'}</p>}</section><details><summary>Source & schedule</summary><p>{active.organization}</p><p>Reported {formatTime(active.reportedAt)}</p><p>Start {formatTime(active.startsAt)}</p><p>Planned end {formatTime(active.plannedEndAt)}</p>{active.schedule && <p>{active.schedule}</p>}{active.comment && <p>{active.comment}</p>}<p>Traffic trend is unknown. Snapshots do not establish speed or clearance.</p></details></>}
            </>}
            <a className="official-link" href={active.source === 'City of Toronto' ? 'https://open.toronto.ca/dataset/traffic-cameras/' : 'https://511on.ca/'} target="_blank" rel="noreferrer">Check official source<ArrowUpRight size={15} /></a>
          </article> : <div className="explore-results">{showing.map((item, index) => <ResultCard key={item.id} item={item} onSelect={select} preview={index < 6} />)}{feed.loading && <p className="empty-state" role="status">Finding official information…</p>}{feed.error && <p className="feed-warning" role="status">{feed.error} Try again shortly.</p>}{!feed.loading && !feed.error && !showing.length && <div className="empty-state"><MapPin size={22} /><h3>No matches in this region</h3><p>Try a category above or select All Ontario. Coverage varies by source.</p></div>}{category === 'explore' && !query && results.length > 4 && <button className="browse-all" onClick={() => chooseCategory('events')}>Browse reported disruptions<ArrowRight size={13} /></button>}{(category !== 'explore' || query) && results.length > limit && <button className="load-more" onClick={() => setLimit(limit + 20)}>Show more results</button>}</div>}
        </section>
        <footer className="explore-footer"><span className={`feed-dot ${feed.stale ? 'delayed' : ''}`} /><div>{feed.fetchedAt ? `Retrieved ${formatTime(feed.fetchedAt)}` : 'Ontario 511'}<small>Official data, as available. Check hours and conditions before travelling.</small><small><a href="https://open.toronto.ca/open-data-licence/" target="_blank" rel="noreferrer">Contains information licensed under the Open Government Licence – Toronto.</a></small></div></footer>
      </aside>
      <div className="map-toolbar"><div className="map-label"><span>{metadata?.label ?? 'EXPLORE THE GTA'}<small>{regions[region].label}</small></span></div><button className="tool reset-tool" aria-label="Return to the Greater Toronto Area" onClick={() => { setSelectedId(null); setRegion('gta'); setResetCount(resetCount + 1); }}><MapPin size={16} /><span>Back to GTA</span></button></div>
      <div className="map-legend"><span><MapPin size={12} /> Select a place to explore</span></div>
    </main>
  </div>;
}

createRoot(document.getElementById('root')).render(<React.StrictMode><App /></React.StrictMode>);
