import { useState, type FormEvent } from 'react'
import { ApiError, getRoom, type RoomOut } from '../api'

interface Props {
  code?: string // set when joining from the lobby list
  onJoined: (room: RoomOut, player: string) => void
  onBack: () => void
}

export function JoinRoom({ code, onJoined, onBack }: Props) {
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  async function submit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault()
    const form = new FormData(e.currentTarget)
    const roomCode = (code ?? String(form.get('code') ?? '')).trim().toUpperCase()
    const player = String(form.get('player') ?? '').trim()
    if (!roomCode) return setError('Enter a room code.')
    if (!player) return setError('Enter your name.')

    setBusy(true)
    setError(null)
    try {
      // The socket doesn't send room details, so fetch them first; this also catches bad codes early
      const room = await getRoom(roomCode)
      if (room.phase !== 'lobby') {
        setError('Game in progress')
        setBusy(false)
        return
      }
      onJoined(room, player)
    } catch (err) {
      setError(err instanceof ApiError && err.status === 404 ? 'Room not found' : "Can't reach the server.")
      setBusy(false)
    }
  }

  return (
    <main>
      <h1>{code ? `Join room ${code}` : 'Join with code'}</h1>
      <form onSubmit={submit} className="stack" noValidate>
        {!code && (
          <label>
            Room code
            <input name="code" maxLength={4} autoComplete="off" autoCapitalize="characters" required />
          </label>
        )}
        <label>
          Your name
          <input name="player" maxLength={20} autoComplete="nickname" required />
        </label>
        {error && <p role="alert" className="error">{error}</p>}
        <div className="actions">
          <button type="submit" className="primary" disabled={busy}>Join</button>
          <button type="button" onClick={onBack}>Back</button>
        </div>
      </form>
    </main>
  )
}
