import { useEffect, useState } from 'react';

export function useFeed(path) {
  const [state, setState] = useState({ items: [], loading: true, stale: false, fetchedAt: null, error: null });
  useEffect(() => {
    let disposed = false;
    let timer;
    let controller;
    if (!path) {
      setState({ items: [], loading: false, stale: false, fetchedAt: null, error: null });
      return;
    }
    setState({ items: [], loading: true, stale: false, fetchedAt: null, error: null });
    async function refresh() {
      controller = new AbortController();
      const timeout = setTimeout(() => controller.abort(), 25000);
      try {
        const response = await fetch(path, { signal: controller.signal });
        if (!response.ok) throw new Error('Feed unavailable');
        const data = await response.json();
        if (!Array.isArray(data.items)) throw new Error('Invalid feed');
        if (!disposed) setState({ ...data, loading: false, error: data.message ?? null });
      } catch {
        if (!disposed) setState((previous) => ({ ...previous, loading: false, stale: true, error: 'This category could not be refreshed. Displayed information may be out of date; retrying shortly.' }));
      } finally {
        clearTimeout(timeout);
        if (!disposed) timer = setTimeout(refresh, 60000);
      }
    }
    refresh();
    return () => { disposed = true; clearTimeout(timer); controller?.abort(); };
  }, [path]);
  return state;
}

export function formatTime(value) {
  return value ? new Intl.DateTimeFormat('en-CA', { month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit', timeZone: 'America/Toronto' }).format(new Date(value)) : 'Not supplied';
}

export function distanceKm(a, b) {
  const radians = (value) => value * Math.PI / 180;
  const lat = radians(b[1] - a[1]);
  const lon = radians(b[0] - a[0]);
  const h = Math.sin(lat / 2) ** 2 + Math.cos(radians(a[1])) * Math.cos(radians(b[1])) * Math.sin(lon / 2) ** 2;
  return 6371 * 2 * Math.atan2(Math.sqrt(h), Math.sqrt(Math.max(0, 1 - h)));
}
