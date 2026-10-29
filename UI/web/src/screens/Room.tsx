import { difficultyLabel, type RoomOut } from '../api'
import { Chat } from '../room/Chat'
import { Generating } from '../room/Generating'
import { Lobby } from '../room/Lobby'
import { Question } from '../room/Question'
import { Results } from '../room/Results'
import { useRoomSocket } from '../socket'

interface Props {
  room: RoomOut
  player: string
  onLeave: () => void
}

const CLOSE_MESSAGES: Record<number, string> = {
  4004: 'Room not found',
  4009: 'That name is taken in this room',
}

export function Room({ room, player, onLeave }: Props) {
  const { state, closeCode, send } = useRoomSocket(room, player)

  if (closeCode !== null) {
    return (
      <main>
        <p role="alert" className="error">{CLOSE_MESSAGES[closeCode] ?? 'Disconnected'}</p>
        <button className="primary" onClick={onLeave}>Back to home</button>
      </main>
    )
  }

  return (
    <main>
      <header className="room-header">
        <div>
          <h1>{room.room_name}</h1>
          <p className="muted">Trivia · {room.topic} · {difficultyLabel[room.difficulty]}</p>
        </div>
        <div className="room-code">
          <span>Code</span> <strong>{room.room_code}</strong>
          <button onClick={() => navigator.clipboard?.writeText(room.room_code)} aria-label="Copy room code">
            Copy
          </button>
        </div>
      </header>
      {state.error && <p role="alert" className="error">{state.error}</p>}
      {state.phase === 'lobby' && <Lobby players={state.players} me={player} onStart={() => send({ type: 'start_game' })} />}
      {state.phase === 'generating' && <Generating />}
      {state.phase === 'question' && state.question && (
        <Question
          key={state.question.index}
          question={state.question}
          onAnswer={answer_index => send({ type: 'submit_answer', answer_index })}
        />
      )}
      {state.phase === 'results' && <Results scores={state.scores} onHome={onLeave} />}
      <Chat messages={state.chat} onSend={text => send({ type: 'chat', text })} />
      <button onClick={onLeave}>Leave room</button>
    </main>
  )
}
