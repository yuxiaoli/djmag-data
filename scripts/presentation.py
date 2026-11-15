"""Source-backed presentation, without inferring biographical or previous-rank facts."""
def description(record):
    ranking=record['rankings'][-1]
    parts=[f"{record['name']} ranked #{ranking['rank']} in DJ Mag's {ranking['year']} poll."]
    if record.get('origin'):parts.append('From: '+record['origin'].rstrip('.')+'.')
    if record.get('styles'):parts.append('DJ style: '+'; '.join(record['styles']).rstrip('.')+'.')
    if record.get('best_known_for'):parts.append('Best known for: '+record['best_known_for'].rstrip('.')+'.')
    return ' '.join(parts)
def movement(record):
    metadata=record.get('profile_metadata') or {}
    raw=metadata.get('movement')
    if not raw:return 'Not shown by source'
    places=metadata.get('movement_places')
    return str(raw)+(f' · {places} places' if places is not None else '')
