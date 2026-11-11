import hashlib
from datetime import datetime, timezone

from api.feeds import coordinates, normalize_events, timestamp


RESOURCES = {
    'construction': ('constructionprojects', 'Construction', 300, 2),
    'road-conditions': ('roadconditions', 'Road conditions', 300, 3),
    'transit-hubs': ('transithub', 'Transit hub', 3600, 2),
    'carpool-lots': ('carpoollots', 'Carpool lot', 3600, 2),
    'ferries': ('ferryterminals', 'Ferry terminal', 60, 2),
    'service-centres': ('servicecentres', 'Service centre', 3600, 2),
    'travel-info': ('informationcenter', 'Travel info centre', 3600, 2),
    'hov-lanes': ('hovlanes', 'HOT / HOV lane', 3600, 2),
    'truck-rest-areas': ('truckrestareas', 'Truck rest area', 3600, 2),
    'inspection-stations': ('inspectionstations', 'Inspection station', 3600, 2),
    'roundabouts': ('roundabouts', 'Roundabout', 3600, 2),
    'seasonal-loads': ('seasonalloadapi', 'Seasonal load restriction', 300, 2),
    'rest-areas': ('allrestareas', 'Rest area', 3600, 2),
}

FACT_FIELDS = {
    'Status': 'Reported status', 'Open': 'Season / hours', 'ParkingSpaces': 'Total parking spaces',
    'AccessibleSpaces': 'Accessible spaces', 'EnterLotFrom': 'Entrance', 'Bike': 'Bike racks',
    'Lights': 'Lighting', 'Transit': 'Transit stop', 'FoodServices': 'Food services',
    'Amenities': 'Amenities', 'FuelProvider': 'Fuel provider', 'CommercialParking': 'Commercial parking',
    'Fuel': 'Fuel', 'Lavatory': 'Washrooms', 'Accessible': 'Accessibility', 'TruckParking': 'Truck parking',
    'OperatedBy': 'Operator', 'Visibility': 'Visibility', 'Drifting': 'Drifting snow',
    'Direction': 'Direction', 'Date': 'Restriction start date', 'Type': 'Type',
}


def text(value):
    if isinstance(value, list):
        return ', '.join(str(part) for part in value if isinstance(part, (str, int, float)))[:2000]
    return str(value)[:4000] if isinstance(value, (str, int, float)) else ''


def decode_polyline(value):
    if not isinstance(value, str) or len(value) > 200000:
        return []
    points, index, lat, lon = [], 0, 0, 0
    try:
        while index < len(value):
            deltas = []
            for _ in range(2):
                result, shift = 0, 0
                while True:
                    byte = ord(value[index]) - 63
                    index += 1
                    if not 0 <= byte <= 63 or shift > 30:
                        return []
                    result |= (byte & 31) << shift
                    shift += 5
                    if byte < 32:
                        break
                deltas.append(~(result >> 1) if result & 1 else result >> 1)
            lat += deltas[0]
            lon += deltas[1]
            point = coordinates({'Latitude': lat / 100000, 'Longitude': lon / 100000})
            if point is None:
                return []
            points.append(point)
    except IndexError:
        return []
    return points


def normalize_resource(category, rows):
    if category == 'construction':
        return [{**item, 'id': item['id'].replace('511-event-', '511-project-')} for item in normalize_events([{**row, 'EventType': 'roadwork'} for row in rows])]
    result = []
    label = RESOURCES[category][1]
    for row in rows:
        position = coordinates(row)
        segments = []
        if category == 'road-conditions':
            raw = row.get('EncodedPolyline', [])
            for encoded in raw if isinstance(raw, list) else [raw]:
                points = decode_polyline(encoded)
                if points:
                    segments.append(points)
            if not segments:
                continue
            longest = max(segments, key=len)
            position = longest[len(longest) // 2]
        if position is None:
            continue
        name = text(row.get('Name') or row.get('SegmentName') or row.get('LocationDescription') or row.get('RoadwayName') or row.get('Highway') or label)
        if category == 'road-conditions':
            name = text(row.get('RoadwayName') or 'Road segment')
        location = text(row.get('Address') or row.get('Location') or row.get('LocationDescription') or row.get('RouteDescription') or row.get('AccessVia') or row.get('Region'))
        identity = str(row.get('Id')) if row.get('Id') is not None else hashlib.sha256(f'{name}|{location}|{position}'.encode()).hexdigest()[:24]
        title = text(row.get('Condition') or row.get('Status') or row.get('Amenities') or row.get('Roadway') or row.get('Highway') or location or label)
        facts = [{'label': caption, 'value': {'Y': 'Yes', 'N': 'No'}.get(text(row[field]), text(row[field]))} for field, caption in FACT_FIELDS.items() if text(row.get(field))]
        updated = timestamp(row.get('LastUpdated'))
        condition_unknown = category == 'road-conditions' and (not updated or (datetime.now(timezone.utc) - datetime.fromisoformat(updated)).total_seconds() > 21600 or title.lower() in ('no report', 'unknown'))
        result.append({
            'id': f'511-{category}-{identity}', 'type': category, 'label': label,
            'road': name, 'location': location, 'title': title,
            'description': text(row.get('Details') or row.get('Comments') or row.get('RouteDescription') or row.get('Amenities') or location),
            'coordinates': position, 'source': 'Ontario 511', 'severity': 'unknown',
            'updatedAt': updated, 'facts': facts, 'segments': segments, 'conditionUnknown': condition_unknown,
        })
    return result
