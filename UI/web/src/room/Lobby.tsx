interface Props {
  players: string[]
  me: string
  host: string | null
  onStart: () => void
}

export function Lobby({ players, me, host, onStart }: Props) {
  return (
    <section aria-label="Players">
      <h2>Players ({players.length})</h2>
      <ul className="players">
        {players.map(p => (
          <li key={p}>
            {p}
            {p === me && <span className="muted"> (you)</span>}
          </li>
        ))}
      </ul>
      <p className="muted">Share the room code above so friends can join.</p>
      {host === me
        ? <button className="primary" onClick={onStart}>Start game</button>
        : <p className="muted">{host ? `Waiting for ${host} to start` : 'Joining…'}</p>}
    </section>
  )
}
