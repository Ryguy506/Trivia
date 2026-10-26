import { useEffect, useState } from 'react'
import { listRooms, type RoomOut } from '../api'

export const POLL_MS = 5000

export function LobbyList({ onJoin }: { onJoin: (code: string) => void }) {
  const [rooms, setRooms] = useState<RoomOut[] | null>(null)
  const [unreachable, setUnreachable] = useState(false)

  useEffect(() => {
    let mounted = true
    const load = () =>
      listRooms().then(
        list => { if (mounted) { setRooms(list); setUnreachable(false) } },
        () => { if (mounted) setUnreachable(true) },
      )
    load()
    const timer = setInterval(load, POLL_MS)
    return () => { mounted = false; clearInterval(timer) }
  }, [])

  return (
    <section aria-labelledby="lobby-heading">
      <h2 id="lobby-heading">Open rooms</h2>
      {unreachable && <p role="alert">Can't reach the server. Retrying…</p>}
      {rooms === null && !unreachable && <p>Loading rooms…</p>}
      {rooms?.length === 0 && <p>No rooms yet</p>}
      {rooms && rooms.length > 0 && (
        <ul className="room-list">
          {rooms.map(r => (
            <li key={r.room_code} className="room-row">
              <div>
                <strong>{r.room_name}</strong>
                <span className="muted"> · {r.topic} · {r.mode === 'trivia' ? 'Trivia' : r.mode}</span>
                <div className="muted">{r.players.length} {r.players.length === 1 ? 'player' : 'players'}</div>
              </div>
              {r.phase === 'lobby'
                ? <button onClick={() => onJoin(r.room_code)} aria-label={`Join ${r.room_name}`}>Join</button>
                : <span className="muted">In progress</span>}
            </li>
          ))}
        </ul>
      )}
    </section>
  )
}
