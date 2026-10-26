import { useEffect, useState, type FormEvent } from 'react'
import { ApiError, createRoom, listCategories, type RoomOut } from '../api'

interface Props {
  onCreated: (room: RoomOut, player: string) => void
  onBack: () => void
}

// Mirrors the server's limits (dto.py) so most mistakes never leave the browser; the server still checks
function validate(name: string, topic: string, player: string): string | null {
  if (!name) return 'Give the room a name.'
  if (topic.length < 2) return 'The topic needs at least 2 characters.'
  if (!player) return 'Enter your name.'
  return null
}

export function CreateRoom({ onCreated, onBack }: Props) {
  const [suggestions, setSuggestions] = useState<string[]>([])
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  useEffect(() => {
    listCategories().then(setSuggestions, () => {}) // suggestions are optional; typing still works
  }, [])

  async function submit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault()
    const form = new FormData(e.currentTarget)
    const field = (key: string) => String(form.get(key) ?? '').trim()
    const name = field('room_name')
    const topic = field('topic')
    const player = field('player')
    const problem = validate(name, topic, player)
    if (problem) return setError(problem)

    setBusy(true)
    setError(null)
    try {
      const room = await createRoom({ room_name: name, room_description: field('room_description'), topic, mode: 'trivia' })
      onCreated(room, player)
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Can't reach the server.")
      setBusy(false)
    }
  }

  return (
    <main>
      <h1>Create room</h1>
      <form onSubmit={submit} className="stack" noValidate>
        <label>
          Room name
          <input name="room_name" maxLength={50} required />
        </label>
        <label>
          Description <span className="muted">(optional)</span>
          <input name="room_description" maxLength={200} />
        </label>
        <label>
          Game mode
          <select name="mode" defaultValue="trivia">
            <option value="trivia">Trivia</option>
          </select>
        </label>
        <label>
          Topic
          <input name="topic" list="topic-suggestions" maxLength={80} placeholder="e.g. Volcanoes" required />
        </label>
        <datalist id="topic-suggestions">
          {suggestions.map(s => <option key={s} value={s} />)}
        </datalist>
        <label>
          Your name
          <input name="player" maxLength={20} required autoComplete="nickname" />
        </label>
        {error && <p role="alert" className="error">{error}</p>}
        <div className="actions">
          <button type="submit" className="primary" disabled={busy}>Create room</button>
          <button type="button" onClick={onBack}>Back</button>
        </div>
      </form>
    </main>
  )
}
