interface Props {
  players: string[]
  me: string
  onStart: () => void
}

export function Lobby({ players, me, onStart }: Props) {
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
      <button className="primary" onClick={onStart}>Start game</button>
    </section>
  )
}
