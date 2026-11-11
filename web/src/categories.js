export const categories = [
  { id: 'events', label: 'Disruptions', icon: 'alert', hint: 'Closures and reported incidents' },
  { id: 'cameras', label: 'Cameras', icon: 'camera', hint: 'Look at official road snapshots' },
  { id: 'road-conditions', label: 'Road conditions', icon: 'weather', hint: 'Surface conditions and visibility' },
  { id: 'transit-hubs', label: 'Transit hubs', icon: 'transit', hint: 'Find a station for your trip' },
  { id: 'rest-areas', label: 'Rest areas', icon: 'rest', hint: 'Find a stop along your route' },
  { id: 'service-centres', label: 'Service centres', icon: 'fuel', hint: 'Food, fuel and facilities' },
  { id: 'construction', label: 'Construction', icon: 'construction', hint: 'Planned projects and lane impacts' },
  { id: 'carpool-lots', label: 'Carpool lots', icon: 'parking', hint: 'Parking and transit connections' },
  { id: 'ferries', label: 'Ferries', icon: 'ferry', hint: 'Terminals and reported service status' },
  { id: 'travel-info', label: 'Travel info', icon: 'info', hint: 'Visitor information centres' },
  { id: 'hov-lanes', label: 'HOT / HOV lanes', icon: 'route', hint: 'Official lane locations' },
  { id: 'truck-rest-areas', label: 'Truck rest areas', icon: 'truck', hint: 'Commercial vehicle stops' },
  { id: 'inspection-stations', label: 'Inspection stations', icon: 'truck', hint: 'Official station locations' },
  { id: 'roundabouts', label: 'Roundabouts', icon: 'route', hint: 'Find mapped roundabouts' },
  { id: 'seasonal-loads', label: 'Seasonal loads', icon: 'truck', hint: 'Reported load restrictions' },
];

export function categoryMatches(category, query) {
  return `${category.label} ${category.hint}`.toLowerCase().includes(query.trim().toLowerCase());
}

export function itemMatches(item, query) {
  return `${item.road} ${item.location} ${item.title ?? ''} ${item.description ?? ''} ${item.provider ?? ''} ${(item.facts ?? []).map((fact) => fact.value).join(' ')}`.toLowerCase().includes(query.trim().toLowerCase());
}
