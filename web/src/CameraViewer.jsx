import React, { useEffect, useRef, useState } from 'react';
import { Expand, EyeOff, Maximize, RefreshCw, X, ZoomIn, ZoomOut } from 'lucide-react';
import { formatTime } from './feeds';

export default function CameraViewer({ camera, stale, nearby = [], onSelectCamera }) {
  const dialog = useRef(null);
  const fullscreenPanel = useRef(null);
  const [zoom, setZoom] = useState(1);
  const [dimensions, setDimensions] = useState(null);
  const [fullscreenError, setFullscreenError] = useState('');
  const [viewId, setViewId] = useState(camera.views.find((view) => view.enabled)?.id ?? '');
  const [refresh, setRefresh] = useState(0);
  const [image, setImage] = useState(null);
  const [retrievedAt, setRetrievedAt] = useState(null);
  const [health, setHealth] = useState('unknown');
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);
  const [nextRefresh, setNextRefresh] = useState(0);
  const [now, setNow] = useState(Date.now());
  useEffect(() => {
    const timer = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(timer);
  }, []);
  useEffect(() => {
    if (!viewId) return;
    const controller = new AbortController();
    let objectUrl;
    let disposed = false;
    const timeout = setTimeout(() => controller.abort(), 25000);
    setImage(null);
    setError(null);
    setLoading(true);
    setHealth('unknown');
    setRetrievedAt(null);
    setDimensions(null);
    setZoom(1);
    setNextRefresh(0);
    fetch(`/api/cameras/${encodeURIComponent(camera.id)}/views/${encodeURIComponent(viewId)}/snapshot`, { signal: controller.signal })
      .then(async (response) => {
        if (!response.ok) {
          const error = new Error('Camera unavailable');
          const retry = Number(response.headers.get('Retry-After'));
          error.retrySeconds = retry > 0 ? Math.min(60, retry) : 10;
          throw error;
        }
        const blob = await response.blob();
        if (disposed) return;
        objectUrl = URL.createObjectURL(blob);
        setImage(objectUrl);
        setNextRefresh(Date.now() + 60000);
        setRetrievedAt(response.headers.get('X-Sentinel-Retrieved-At'));
        setHealth(response.headers.get('X-Sentinel-Camera-Health') ?? 'unknown');
      })
      .catch((error) => {
        if (!disposed) {
          setError('The snapshot could not be loaded. The source or connection may be temporarily unavailable.');
          setNextRefresh(Date.now() + (error.retrySeconds ?? 10) * 1000);
        }
      })
      .finally(() => { clearTimeout(timeout); if (!disposed) setLoading(false); });
    return () => { disposed = true; controller.abort(); clearTimeout(timeout); if (objectUrl) URL.revokeObjectURL(objectUrl); };
  }, [camera.id, viewId, refresh]);
  const wait = Math.max(0, Math.ceil((nextRefresh - now) / 1000));
  function closeLarge() {
    if (document.fullscreenElement === fullscreenPanel.current) document.exitFullscreen().catch(() => {});
    dialog.current.close();
  }
  async function fullscreen() {
    try {
      if (document.fullscreenElement) await document.exitFullscreen();
      else await fullscreenPanel.current.requestFullscreen();
      setFullscreenError('');
    } catch {
      setFullscreenError('Fullscreen is unavailable in this browser. The enlarged viewer is still available.');
    }
  }
  const imageSource = viewId.startsWith('511-') ? 'Ontario 511' : camera.source;
  const sourceLink = imageSource === 'City of Toronto' ? 'https://open.toronto.ca/dataset/traffic-cameras/' : 'https://511on.ca/';
  return <section className="camera-viewer" aria-label="Official camera snapshot">
    <div className="camera-source"><span>SNAPSHOT · {imageSource.toUpperCase()}</span><strong>{camera.provider}</strong></div>
    {stale && <p className="camera-warning" role="status">Some camera metadata is delayed or unavailable. Coverage and availability may have changed.</p>}
    {camera.views.length > 1 && <label className="view-selector">Camera view<select aria-label="Camera view" value={viewId} onChange={(event) => setViewId(event.target.value)}>{camera.views.filter((view) => view.enabled).map((view, index) => <option key={view.id} value={view.id}>{view.description === 'Camera view' ? `View ${index + 1}` : view.description}</option>)}</select></label>}
    <div className={error ? 'snapshot-frame snapshot-failed' : 'snapshot-frame'} aria-live="polite">
      {loading && <p>Retrieving official image…</p>}
      {!viewId && <p>No enabled image view is available. Conditions are unknown.</p>}
      {error && <div className="camera-unavailable" role="status"><EyeOff size={25} /><h4>This image could not load</h4><p>{error}</p>{nearby[0] && <button onClick={() => onSelectCamera(nearby[0])}>Try {nearby[0].road} / {nearby[0].location}<small>{nearby[0].distance.toFixed(1)} km away · a different camera</small></button>}</div>}
      {image && <img src={image} alt={`${camera.road}: ${camera.location}. Official snapshot; capture time unverified.`} onLoad={(event) => setDimensions([event.currentTarget.naturalWidth, event.currentTarget.naturalHeight])} onError={() => { setImage(null); setError('The image could not be displayed. Try again or choose another camera.'); setNextRefresh(Date.now() + 10000); }} />}
    </div>
    {image && <button className="expand-camera" onClick={() => { setZoom(1); dialog.current.showModal(); }}><Expand size={15} /> Open larger view</button>}
    {dimensions && <p className="snapshot-time">Original image: {dimensions[0]} × {dimensions[1]} pixels. Zoom enlarges the source without adding detail.</p>}
    {health === 'frozen' && <p className="camera-warning">Same image as a check at least 10 minutes ago. The feed may be frozen; conditions are unknown.</p>}
    {health === 'unchanged' && <p className="camera-warning">Image unchanged since the last check. Freshness is unverified.</p>}
    {retrievedAt && image && <p className="snapshot-time">Image retrieved: {formatTime(retrievedAt)} (Toronto time)<br />Capture time is unverified. This is a still image, not live video. The provider may display an offline notice.</p>}
    {error && <p className="snapshot-time">No image was retrieved. Road conditions are unknown.</p>}
    <button className="refresh-image" disabled={loading || wait > 0 || !viewId} onClick={() => setRefresh(refresh + 1)}><RefreshCw size={13} />{loading ? 'Loading snapshot…' : wait > 0 ? `${error ? 'Retry' : 'Refresh'} available in ${wait}s` : error ? 'Try this camera again' : 'Refresh snapshot'}</button>
    {nearby.length > 0 && <section className="nearby-cameras"><h4>Try another nearby angle</h4><p>Different cameras may face different streets.</p>{nearby.map((next) => <button key={next.id} onClick={() => onSelectCamera(next)}><span>{next.road}<small>{next.location} · {next.distance.toFixed(1)} km</small></span></button>)}</section>}
    <p className="snapshot-time">Source: <a href={sourceLink} target="_blank" rel="noreferrer">{imageSource}</a>{camera.alsoListedBy && ` · Also listed by ${camera.alsoListedBy}`}</p>
    <dialog ref={dialog} className="camera-dialog" aria-labelledby="camera-dialog-title" onClose={() => setZoom(1)}>
      <div ref={fullscreenPanel} className="camera-fullscreen-panel">
      <header><div><span className="eyebrow">OFFICIAL SNAPSHOT · {imageSource}</span><h2 id="camera-dialog-title">{camera.road}</h2><p>{camera.location}</p></div><button className="icon-button" aria-label="Close enlarged camera" onClick={closeLarge}><X size={22} /></button></header>
      <div className="camera-controls"><button aria-label="Zoom out camera image" disabled={zoom <= 1} onClick={() => setZoom(Math.max(1, zoom - 0.5))}><ZoomOut size={16} /></button><span aria-live="polite">{Math.round(zoom * 100)}%</span><button aria-label="Zoom in camera image" disabled={zoom >= 4} onClick={() => setZoom(Math.min(4, zoom + 0.5))}><ZoomIn size={16} /></button><button onClick={() => setZoom(1)}>Fit image</button>{document.fullscreenEnabled && <button onClick={fullscreen}><Maximize size={15} /> Fullscreen</button>}</div>
      <div className="camera-zoom-stage">{image ? <img src={image} style={{ width: `${zoom * 100}%` }} alt={`${camera.road} at ${camera.location}. Still image, capture time unverified.`} /> : <p>{error ?? 'Retrieving official image…'}</p>}</div>
      {fullscreenError && <p className="camera-warning" role="status">{fullscreenError}</p>}
      <p className="snapshot-time">Retrieved {formatTime(retrievedAt)} · {dimensions ? `${dimensions[0]} × ${dimensions[1]} source pixels` : 'Source resolution unavailable'}<br />Still image; capture time unverified. Enlarging does not add detail. {health === 'frozen' ? 'This feed may be frozen.' : health === 'unchanged' ? 'Image unchanged since the previous check.' : ''}{stale ? ' Camera metadata is delayed.' : ''}</p>
      {nearby.length > 0 && <div className="camera-nearby-strip"><span>Nearby views</span>{nearby.map((next) => <button key={next.id} onClick={() => { closeLarge(); onSelectCamera(next); }}>{next.road} / {next.location}</button>)}</div>}
      </div>
    </dialog>
  </section>;
}
