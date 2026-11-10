import React, { useEffect, useState } from 'react';
import { RefreshCw } from 'lucide-react';
import { formatTime } from './feeds';

export default function CameraViewer({ camera, stale }) {
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
    setNextRefresh(Date.now() + 60000);
    fetch(`/api/cameras/${encodeURIComponent(camera.id)}/views/${encodeURIComponent(viewId)}/snapshot`, { signal: controller.signal })
      .then(async (response) => {
        if (!response.ok) throw new Error('Camera unavailable');
        const blob = await response.blob();
        if (disposed) return;
        objectUrl = URL.createObjectURL(blob);
        setImage(objectUrl);
        setRetrievedAt(response.headers.get('X-Sentinel-Retrieved-At'));
        setHealth(response.headers.get('X-Sentinel-Camera-Health') ?? 'unknown');
      })
      .catch(() => { if (!disposed) setError('Image unavailable. Road conditions are unknown.'); })
      .finally(() => { clearTimeout(timeout); if (!disposed) setLoading(false); });
    return () => { disposed = true; controller.abort(); clearTimeout(timeout); if (objectUrl) URL.revokeObjectURL(objectUrl); };
  }, [camera.id, viewId, refresh]);
  const wait = Math.max(0, Math.ceil((nextRefresh - now) / 1000));
  return <section className="camera-viewer" aria-label="Official camera snapshot">
    <div className="camera-source"><span>SNAPSHOT · ONTARIO 511</span><strong>{camera.provider}</strong></div>
    {stale && <p className="camera-warning" role="status">Camera metadata is stale. Availability may have changed.</p>}
    {camera.views.length > 1 && <label className="view-selector">Camera view<select aria-label="Camera view" value={viewId} onChange={(event) => setViewId(event.target.value)}>{camera.views.filter((view) => view.enabled).map((view, index) => <option key={view.id} value={view.id}>{view.description === 'Camera view' ? `View ${index + 1}` : view.description}</option>)}</select></label>}
    <div className="snapshot-frame" aria-live="polite">
      {loading && <p>Retrieving official image…</p>}
      {!viewId && <p>No enabled image view is available. Conditions are unknown.</p>}
      {error && <p role="status">{error}</p>}
      {image && <img src={image} alt={`${camera.road}: ${camera.location}. Official snapshot; capture time unverified.`} onError={() => { setImage(null); setError('Image could not be displayed. Conditions are unknown.'); }} />}
    </div>
    {health === 'frozen' && <p className="camera-warning">Same image as a check at least 10 minutes ago. The feed may be frozen; conditions are unknown.</p>}
    {health === 'unchanged' && <p className="camera-warning">Image unchanged since the last check. Freshness is unverified.</p>}
    <p className="snapshot-time">Image retrieved: {formatTime(retrievedAt)} (Toronto time)<br />Capture time is unverified. This is a still image, not live video. The provider may display an offline notice.</p>
    <button className="refresh-image" disabled={loading || wait > 0 || !viewId} onClick={() => setRefresh(refresh + 1)}><RefreshCw size={13} />{wait > 0 ? `Refresh available in ${wait}s` : 'Refresh snapshot'}</button>
  </section>;
}
