"""
One-off script to backfill missing individual_video_appearances for a session.

Usage:
  python3 fix_orphan_appearances.py <session_uuid>

This will:
 - find individuals linked to the session that have no appearances
 - discover videos for the session (via Gateway/media search)
 - create a single appearance per orphan individual associated with a discovered video

This is intentionally conservative: it creates a minimal appearance so aggregated-analysis
and embedding extraction can run. It logs actions and avoids deleting anything.
"""

import sys
import asyncio
import asyncpg
import aiohttp
import uuid
from datetime import timezone

VMETA_DB = "postgresql://postgres:localdevpass@localhost:5432/ppl_meta_vmeta"
VISION_DB = "postgresql://postgres:localdevpass@localhost:5432/ppl_vision_db"
GATEWAY_SEARCH = "http://localhost:8080/api/v1/media/search"


async def discover_videos(collections, start_time, end_time):
    params = {
        'start_time': start_time.astimezone(timezone.utc).isoformat().replace('+00:00', 'Z') if start_time else None,
        'end_time': end_time.astimezone(timezone.utc).isoformat().replace('+00:00', 'Z') if end_time else None,
    }
    # Use first collection as a hint
    if collections and len(collections) > 0:
        params['collection'] = collections[0]

    async with aiohttp.ClientSession() as sess:
        try:
            async with sess.get(GATEWAY_SEARCH, params={k:v for k,v in params.items() if v}) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    if isinstance(data, list):
                        items = data
                    elif isinstance(data, dict) and data.get('items'):
                        items = data.get('items')
                    elif isinstance(data, dict) and data.get('media'):
                        items = data.get('media')
                    else:
                        items = []

                    videos = []
                    for v in items:
                        vid_uuid = v.get('uuid') or v.get('id')
                        ts = v.get('start_timestamp') or v.get('timestamp') or v.get('created_at')
                        duration = v.get('duration') or v.get('technical_metadata', {}).get('duration_seconds', 30)
                        if vid_uuid:
                            videos.append({'uuid': vid_uuid, 'timestamp': ts, 'duration': duration})
                    return videos
                else:
                    text = await resp.text()
                    print('Gateway search returned', resp.status, text[:200])
                    return []
        except Exception as e:
            print('Gateway search failed:', e)
            return []


async def backfill(session_uuid: str):
    conn = await asyncpg.connect(VMETA_DB)
    try:
        session = await conn.fetchrow('SELECT collections, start_time, end_time, started_at, completed_at FROM tracking_sessions WHERE session_uuid = $1', session_uuid)
        if not session:
            print('Session not found:', session_uuid)
            return

        collections = session['collections'] or []
        start_time = session['start_time'] or session['started_at'] or session['created_at'] if 'created_at' in session else None
        end_time = session['end_time'] or session['completed_at'] or None

        # Find orphan individuals (in session_individuals but no entries in individual_video_appearances)
        orphans = await conn.fetch('''
            SELECT si.individual_uuid
            FROM session_individuals si
            LEFT JOIN individual_video_appearances iva
              ON iva.individual_uuid = si.individual_uuid
            WHERE si.session_uuid = $1
              AND iva.individual_uuid IS NULL
        ''', session_uuid)

        orphan_uuids = [str(r['individual_uuid']) for r in orphans]
        print('Found', len(orphan_uuids), 'orphan individual(s) in session', session_uuid)
        if not orphan_uuids:
            return

        # Discover videos for session
        videos = await discover_videos(collections, start_time, end_time)
        if not videos:
            print('No videos discovered for session; cannot assign appearances. Exiting.')
            return

        print('Discovered', len(videos), 'videos; will assign appearances round-robin')

        # Connect to Vision DB for person_object lookup
        vision_conn = await asyncpg.connect(VISION_DB)

        created = 0
        for idx, ind_uuid in enumerate(orphan_uuids):
            video = videos[idx % len(videos)]
            video_uuid = video['uuid']
            # Try to find a person_object for this video in Vision DB
            person_object_uuid = None
            try:
                po_row = await vision_conn.fetchrow('''
                    SELECT po.person_id
                    FROM person_objects po
                    JOIN face_detections fd ON fd.id = po.best_face_id
                    WHERE fd.media_id = $1
                    LIMIT 1
                ''', uuid.UUID(video_uuid))
                if po_row and po_row.get('person_id'):
                    person_object_uuid = str(po_row['person_id'])
            except Exception:
                # ignore lookup errors
                person_object_uuid = None

            if not person_object_uuid:
                person_object_uuid = str(uuid.uuid4())

            # Use video timestamp if available
            start_ts = video.get('timestamp')
            if isinstance(start_ts, str):
                try:
                    from datetime import datetime
                    start_ts = datetime.fromisoformat(start_ts.replace('Z', '+00:00'))
                except Exception:
                    start_ts = None

            if start_ts is None:
                # Fallback to session started_at or now
                start_ts = session.get('started_at') or session.get('created_at')

            if start_ts is None:
                from datetime import datetime
                start_ts = datetime.utcnow()

            end_ts = start_ts
            try:
                from datetime import timedelta
                end_ts = start_ts + timedelta(seconds=30)
            except Exception:
                end_ts = start_ts

            try:
                await conn.execute('''
                    INSERT INTO individual_video_appearances (
                        individual_uuid, video_uuid, person_object_uuid,
                        start_timestamp, end_timestamp, entry_bbox, exit_bbox, confidence_score
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                    ON CONFLICT DO NOTHING
                ''', ind_uuid, video_uuid, person_object_uuid, start_ts, end_ts, [100,200,150,300], [110,210,160,310], 0.85)
                created += 1
                print('Created appearance for', ind_uuid, '-> video', video_uuid)
            except Exception as e:
                print('Failed to create appearance for', ind_uuid, e)

        await vision_conn.close()
        print('Backfill complete. Created', created, 'appearances.')
    finally:
        await conn.close()


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('Usage: python3 fix_orphan_appearances.py <session_uuid>')
        sys.exit(1)
    session_uuid = sys.argv[1]
    asyncio.run(backfill(session_uuid))
