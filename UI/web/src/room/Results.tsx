export function Results({ scores, onHome }: { scores: Record<string, number> | null; onHome: () => void }) {
  if (!scores) return <p>Adding up scores…</p>
  const ranked = Object.entries(scores).sort(([, a], [, b]) => b - a)

  return (
    <section aria-label="Results" className="results">
      <h2>Results</h2>
      <table>
        <thead>
          <tr><th scope="col">Player</th><th scope="col">Score</th></tr>
        </thead>
        <tbody>
          {ranked.map(([player, score]) => (
            <tr key={player}><td>{player}</td><td>{score}</td></tr>
          ))}
        </tbody>
      </table>
      <button className="primary" onClick={onHome}>Back to home</button>
    </section>
  )
}
