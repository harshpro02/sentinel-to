import React, { useEffect, useRef, useState } from 'react';
import { BoundingSphere, Cartesian2, Cartesian3, Color, CustomDataSource, defined, DistanceDisplayCondition, HeadingPitchRange, ImageryLayer, Ion, LabelStyle, Math as CesiumMath, Matrix4, NearFarScalar, OpenStreetMapImageryProvider, ScreenSpaceEventHandler, ScreenSpaceEventType, Viewer } from 'cesium';
import 'cesium/Build/Cesium/Widgets/widgets.css';
import { categories } from './categories';

export const regions = {
  gta: { label: 'Greater Toronto Area', coordinates: [-79.55, 43.8], range: 65000, bounds: [-80.3, 43.2, -78.5, 44.5] },
  southern: { label: 'Southern Ontario', coordinates: [-80.5, 44.1], range: 550000, bounds: [-83.2, 41.6, -77.5, 45.8] },
  eastern: { label: 'Eastern Ontario', coordinates: [-76.5, 45.0], range: 320000, bounds: [-78.5, 43.6, -74.2, 46.4] },
  northern: { label: 'Northern Ontario', coordinates: [-85.0, 49.5], range: 1250000, bounds: [-95.2, 45.8, -79.0, 56.9] },
  province: { label: 'All Ontario', coordinates: [-85.0, 49.0], range: 1900000, bounds: [-95.2, 41.6, -74.2, 56.9] },
};

const reducedMotion = () => window.matchMedia('(prefers-reduced-motion: reduce)').matches;
const markerImages = new Map();
const markerPaths = {
  camera: '<rect x="8" y="11" width="16" height="11" rx="2"/><circle cx="16" cy="16.5" r="3"/>',
  incident: '<path d="M16 8 25 24H7Z"/><path d="M16 13v5m0 3v.2"/>',
  construction: '<path d="M8 12h16v9H8Zm3 0 7 9m0-9 6 8M10 21v4m12-4v4"/>',
  'transit-hubs': '<rect x="9" y="8" width="14" height="16" rx="3"/><path d="M9 16h14m-11 5h1m6 0h1m-9 3-2 3m12-3 2 3"/>',
  'rest-areas': '<path d="M9 12h12v8a4 4 0 0 1-4 4h-4a4 4 0 0 1-4-4Zm12 0h2a3 3 0 0 1 0 6h-2M12 7v2m5-2v2"/>',
  'service-centres': '<path d="M9 25V9h11v16M9 15h11m0-5 4 4v8a2 2 0 0 0 4 0v-5l-3-3M7 25h15"/>',
};
function markerImage(kind, active = false) {
  const key = `${kind}-${active}`;
  if (!markerImages.has(key)) {
    const color = active ? '#a9e8d0' : kind === 'incident' ? '#f2a28f' : kind === 'construction' ? '#e5c188' : '#b0d9d0';
    const path = markerPaths[kind] ?? '<circle cx="16" cy="15" r="6"/><path d="m12 20 4 6 4-6"/>';
    markerImages.set(key, `data:image/svg+xml,${encodeURIComponent(`<svg xmlns="http://www.w3.org/2000/svg" width="34" height="38" viewBox="0 0 32 36"><path d="M16 35 11 29H7a6 6 0 0 1-6-6V7a6 6 0 0 1 6-6h18a6 6 0 0 1 6 6v16a6 6 0 0 1-6 6h-4Z" fill="#152b35" stroke="${color}" stroke-width="1.5"/><g fill="none" stroke="${color}" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round">${path}</g></svg>`)}`);
  }
  return markerImages.get(key);
}

export default function OntarioMap({ items, selected, onSelect, tilted, region, resetCount }) {
  const container = useRef(null);
  const viewer = useRef(null);
  const markers = useRef(null);
  const selectRef = useRef(onSelect);
  const itemsRef = useRef(items);
  const [ready, setReady] = useState(false);
  const [mapError, setMapError] = useState('');
  const [hovered, setHovered] = useState(null);
  selectRef.current = onSelect;
  itemsRef.current = items;

  useEffect(() => {
    let instance;
    let handler;
    try {
      Ion.defaultAccessToken = '';
      const imagery = new OpenStreetMapImageryProvider({ url: 'https://tile.openstreetmap.org/', maximumLevel: 19 });
      imagery.errorEvent.addEventListener(() => setMapError('Some street imagery could not load. You can still browse the incident list.'));
      instance = new Viewer(container.current, {
        baseLayer: new ImageryLayer(imagery, { brightness: 0.94, saturation: 0.55 }),
        baseLayerPicker: false, geocoder: false, animation: false, timeline: false,
        homeButton: false, sceneModePicker: false, navigationHelpButton: false,
        fullscreenButton: false, infoBox: false, selectionIndicator: false,
        requestRenderMode: true, maximumRenderTimeChange: Infinity,
      });
      viewer.current = instance;
      const source = new CustomDataSource('reports');
      markers.current = source;
      instance.dataSources.add(source);
      source.clustering.enabled = true;
      source.clustering.pixelRange = 55;
      source.clustering.minimumClusterSize = 3;
      source.clustering.clusterEvent.addEventListener((entities, cluster) => {
        cluster.billboard.show = true;
        cluster.point.show = false;
        cluster.label.show = false;
        const kinds = entities.map((entity) => entity.properties.kind.getValue());
        const kind = kinds.includes('incident') ? 'incident' : kinds[0];
        const caption = kind === 'incident' ? 'Road reports' : kind === 'camera' ? 'Cameras' : kind === 'construction' ? 'Roadwork' : categories.find((entry) => entry.id === kind)?.label ?? 'Places';
        cluster.label.text = `${caption} nearby`;
        cluster.label.font = '500 11px sans-serif';
        cluster.label.fillColor = Color.WHITE;
        cluster.label.outlineWidth = 0;
        cluster.label.showBackground = true;
        cluster.label.backgroundColor = Color.fromCssColorString('#263e49');
        cluster.label.backgroundPadding = new Cartesian2(10, 8);
        cluster.label.pixelOffset = Cartesian2.ZERO;
        cluster.label.disableDepthTestDistance = Infinity;
        cluster.label.id = { clusterMembers: entities.map((entity) => entity.position.getValue(instance.clock.currentTime)) };
        cluster.billboard.image = markerImage(kind);
        cluster.billboard.width = 34;
        cluster.billboard.height = 38;
        cluster.billboard.id = { ...cluster.label.id, caption: `Explore nearby ${caption.toLowerCase()}` };
        cluster.billboard.disableDepthTestDistance = Infinity;
      });
      instance.scene.backgroundColor = Color.fromCssColorString('#0a1016');
      instance.scene.globe.baseColor = Color.fromCssColorString('#172530');
      instance.scene.globe.enableLighting = false;
      instance.scene.screenSpaceCameraController.minimumZoomDistance = 120;
      instance.scene.screenSpaceCameraController.maximumZoomDistance = 4000000;
      const initial = regions.gta;
      instance.camera.lookAt(Cartesian3.fromDegrees(...initial.coordinates), new HeadingPitchRange(0, -Math.PI / 2, initial.range));
      instance.camera.lookAtTransform(Matrix4.IDENTITY);
      handler = new ScreenSpaceEventHandler(instance.scene.canvas);
      handler.setInputAction((click) => {
        const picked = instance.scene.pick(click.position);
        if (!defined(picked?.id)) return;
        if (picked.id.clusterMembers) {
          const sphere = BoundingSphere.fromPoints(picked.id.clusterMembers);
          instance.camera.flyToBoundingSphere(sphere, { offset: new HeadingPitchRange(0, -Math.PI / 2, Math.max(sphere.radius * 4, 2500)), duration: reducedMotion() ? 0 : 0.6 });
          return;
        }
        const item = itemsRef.current.find((candidate) => candidate.id === (picked.id.properties?.itemId?.getValue() ?? picked.id.id));
        if (item) selectRef.current(item);
      }, ScreenSpaceEventType.LEFT_CLICK);
      handler.setInputAction((movement) => {
        const picked = instance.scene.pick(movement.endPosition);
        instance.scene.canvas.style.cursor = defined(picked?.id) ? 'pointer' : '';
        const item = itemsRef.current.find((candidate) => candidate.id === (picked?.id?.properties?.itemId?.getValue() ?? picked?.id?.id));
        const caption = picked?.id?.caption ?? (item ? `${item.road} · ${item.type === 'camera' ? 'See snapshot' : item.title}` : null);
        const bounds = instance.scene.canvas.getBoundingClientRect();
        setHovered(caption ? { caption, x: Math.min(bounds.left + movement.endPosition.x + 14, window.innerWidth - 270), y: Math.max(12, bounds.top + movement.endPosition.y - 50) } : null);
      }, ScreenSpaceEventType.MOUSE_MOVE);
      instance.scene.canvas.addEventListener('mouseleave', () => setHovered(null));
      instance.scene.renderError.addEventListener(() => setMapError('The map encountered a rendering error. You can still browse the incident list.'));
      setReady(true);
    } catch {
      setMapError('The map requires WebGL. You can still browse every example in the incident list.');
    }
    return () => {
      handler?.destroy();
      if (instance && !instance.isDestroyed()) instance.destroy();
      viewer.current = null;
    };
  }, []);

  useEffect(() => {
    if (!ready || !viewer.current) return;
    const instance = viewer.current;
    instance.entities.removeAll();
    markers.current.entities.removeAll();
    items.forEach((item) => {
      const active = selected?.id === item.id;
      (active ? instance.entities : markers.current.entities).add({
        id: item.id,
        properties: { kind: item.type },
        position: Cartesian3.fromDegrees(...item.coordinates, 12),
        billboard: { image: markerImage(item.type, active), width: active ? 40 : 30, height: active ? 44 : 34, disableDepthTestDistance: Infinity },
        label: { show: active, text: item.road.toUpperCase(), distanceDisplayCondition: new DistanceDisplayCondition(0, active ? Number.MAX_VALUE : 60000), font: '11px monospace', fillColor: Color.fromCssColorString('#e7edf2'), style: LabelStyle.FILL_AND_OUTLINE, outlineColor: Color.fromCssColorString('#0a1016'), outlineWidth: 4, pixelOffset: new Cartesian2(0, -24), scaleByDistance: new NearFarScalar(250000, 1, 1800000, 0.6), disableDepthTestDistance: Infinity },
      });
      (item.segments ?? []).forEach((segment, index) => {
        if (segment.length > 1) instance.entities.add({
          id: `${item.id}-segment-${index}`, properties: { itemId: item.id },
          polyline: { positions: Cartesian3.fromDegreesArray(segment.flat()), width: active ? 6 : 3, material: Color.fromCssColorString(active ? '#0e8278' : '#527e9c').withAlpha(0.8) },
        });
      });
    });
    instance.scene.requestRender();
  }, [items, selected, ready]);

  useEffect(() => {
    if (!ready || !viewer.current) return;
    const preset = regions[region];
    viewer.current.camera.flyToBoundingSphere(
      new BoundingSphere(Cartesian3.fromDegrees(...(selected?.coordinates ?? preset.coordinates)), 0),
      { offset: new HeadingPitchRange(0, CesiumMath.toRadians(tilted ? -50 : -90), selected ? 16000 : preset.range), duration: reducedMotion() ? 0 : 0.9 },
    );
  }, [selected?.id, tilted, region, resetCount, ready]);

  return <>
    <div ref={container} className="map" role="region" aria-label="Interactive Ontario road map; incident markers have matching accessible list buttons" />
    {mapError && <div className="map-error" role="status">{mapError}</div>}
    {!ready && !mapError && <div className="map-loading" role="status">Loading Ontario map…</div>}
    {hovered && <div className="map-hover" style={{ left: hovered.x, top: hovered.y }}>{hovered.caption}</div>}
  </>;
}
