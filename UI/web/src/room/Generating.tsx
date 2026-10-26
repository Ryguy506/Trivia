export function Generating() {
  return (
    <section className="generating" aria-live="polite">
      <div className="spinner" aria-hidden="true" />
      <p>Generating questions…</p>
      <p className="muted">Reading Wikipedia and writing questions. This takes about half a minute.</p>
    </section>
  )
}
