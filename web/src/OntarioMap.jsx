import React, { useEffect, useRef, useState } from 'react';
import { BoundingSphere, Cartesian2, Cartesian3, Color, defined, DistanceDisplayCondition, HeadingPitchRange, ImageryLayer, Ion, LabelStyle, Math as CesiumMath, Matrix4, NearFarScalar, OpenStreetMapImageryProvider, ScreenSpaceEventHandler, ScreenSpaceEventType, Viewer } from 'cesium';
import 'cesium/Build/Cesium/Widgets/widgets.css';

export const regions = {
  gta: { label: 'Greater Toronto Area', coordinates: [-79.55, 43.8], range: 120000, bounds: [-80.3, 43.2, -78.5, 44.5] },
  southern: { label: 'Southern Ontario', coordinates: [-80.5, 44.1], range: 550000, bounds: [-83.2, 41.6, -77.5, 45.8] },
  eastern: { label: 'Eastern Ontario', coordinates: [-76.5, 45.0], range: 320000, bounds: [-78.5, 43.6, -74.2, 46.4] },
  northern: { label: 'Northern Ontario', coordinates: [-85.0, 49.5], range: 1250000, bounds: [-95.2, 45.8, -79.0, 56.9] },
  province: { label: 'All Ontario', coordinates: [-85.0, 49.0], range: 1900000, bounds: [-95.2, 41.6, -74.2, 56.9] },
};

const reducedMotion = () => window.matchMedia('(prefers-reduced-motion: reduce)').matches;

export default function OntarioMap({ items, selected, onSelect, tilted, region, resetCount }) {
  const container = useRef(null);
  const viewer = useRef(null);
  const selectRef = useRef(onSelect);
  const itemsRef = useRef(items);
  const [ready, setReady] = useState(false);
  const [mapError, setMapError] = useState('');
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
        baseLayer: new ImageryLayer(imagery, { brightness: 0.55, saturation: 0.2 }),
        baseLayerPicker: false, geocoder: false, animation: false, timeline: false,
        homeButton: false, sceneModePicker: false, navigationHelpButton: false,
        fullscreenButton: false, infoBox: false, selectionIndicator: false,
        requestRenderMode: true, maximumRenderTimeChange: Infinity,
      });
      viewer.current = instance;
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
        const item = itemsRef.current.find((candidate) => candidate.id === picked.id.id);
        if (item) selectRef.current(item);
      }, ScreenSpaceEventType.LEFT_CLICK);
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
    items.forEach((item) => {
      const active = selected?.id === item.id;
      instance.entities.add({
        id: item.id,
        position: Cartesian3.fromDegrees(...item.coordinates, 12),
        point: { pixelSize: active ? 17 : 12, color: Color.fromCssColorString(active ? '#a9e8d0' : item.type === 'camera' ? '#93badb' : item.severity === 'high' ? '#f09081' : '#dfb573'), outlineColor: Color.fromCssColorString('#0d151e'), outlineWidth: 4, disableDepthTestDistance: Infinity },
        label: { text: item.road.toUpperCase(), distanceDisplayCondition: new DistanceDisplayCondition(0, active ? Number.MAX_VALUE : 60000), font: '11px monospace', fillColor: Color.fromCssColorString('#e7edf2'), style: LabelStyle.FILL_AND_OUTLINE, outlineColor: Color.fromCssColorString('#0a1016'), outlineWidth: 4, pixelOffset: new Cartesian2(0, -24), scaleByDistance: new NearFarScalar(250000, 1, 1800000, 0.6), disableDepthTestDistance: Infinity },
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
  </>;
}
