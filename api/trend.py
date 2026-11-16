from datetime import datetime, timezone

SEVERITY_RANK = {'low': 1, 'medium': 2, 'high': 3}
COMPARED_FIELDS = ('severity', 'fullClosure', 'title', 'sourceSeverity', 'description')
UNCHANGED_AFTER_SECONDS = 1200
MAX_OBSERVATION_AGE_SECONDS = 300

ADVICE = {
    'increased': 'The latest saved official report describes a greater impact than the preceding version. Check the official source before travelling.',
    'reduced': 'The latest saved official report describes a lower impact than the preceding version. This does not confirm road clearance or a shorter delay.',
    'unchanged': 'The compared reports show no change in reported impact. This does not establish steady traffic or a continuing delay.',
    'unknown': 'There is not enough recent, comparable report evidence. Check the official source for current information.',
}


def escalation(report):
    return 4 if report.get('fullClosure') else SEVERITY_RANK.get(report.get('severity'))


def changed_fields(newest, previous):
    return [field for field in COMPARED_FIELDS if newest.get(field) != previous.get(field)]


def parse(value):
    try:
        parsed = datetime.fromisoformat(value)
        return parsed if parsed.tzinfo is not None else None
    except (TypeError, ValueError):
        return None


def assess(history, now=None):
    now = now or datetime.now(timezone.utc)
    versions = (history.get('versions') or []) if history else []
    count = len(versions)
    if not count:
        return result('unknown', 'none', 0, [], 'No recorded report versions yet.')
    last_seen = parse(history.get('lastSeenAt'))
    if last_seen is None or not 0 <= (now - last_seen).total_seconds() <= MAX_OBSERVATION_AGE_SECONDS:
        return result('unknown', 'none', count, [], 'The latest feed observation is missing, in the future or older than five minutes. This freshness limit is a Sentinel policy, not a provider guarantee.')
    newest = versions[0]['report']
    previous = versions[1]['report'] if count > 1 else newest
    changed = changed_fields(newest, previous)
    new_rank, previous_rank = escalation(newest), escalation(previous)
    if new_rank is None or previous_rank is None:
        return result('unknown', 'none', count, changed, 'Reported impact is unknown in at least one compared version. Missing impact is not evidence of improvement.')
    if count >= 2:
        if new_rank > previous_rank:
            status = 'increased'
        elif new_rank < previous_rank:
            status = 'reduced'
        else:
            status = 'unchanged'
        basis = f'Latest two saved versions: {describe(previous)} to {describe(newest)}. {count} saved versions returned; version count is not a confidence measure.'
        return result(status, 'low', count, changed, basis)
    first_seen = parse(history.get('firstSeenAt'))
    duration = (last_seen - first_seen).total_seconds() if first_seen else -1
    if duration >= UNCHANGED_AFTER_SECONDS:
        return result('unchanged', 'low', count, changed, f'The same report remained listed for {round(duration / 60)} minutes with {describe(newest)}. This does not measure road conditions.')
    return result('unknown', 'none', count, changed, 'Only one recent saved version; no report change is available to compare.')


def describe(report):
    if report.get('fullClosure'):
        return 'a full closure'
    return {'high': 'high severity', 'medium': 'medium severity', 'low': 'low severity'}.get(report.get('severity'), 'unknown severity')


def result(status, confidence, observations, changed, basis):
    return {
        'status': status,
        'confidence': confidence,
        'advice': ADVICE[status],
        'basis': basis,
        'observations': observations,
        'changedFields': changed,
        'note': 'Official report comparison only. Traffic trend remains unknown. Confidence is an unvalidated qualitative label, not a probability. These reports do not establish speed, clearance or a faster route.',
    }
