import { useState, type FormEvent } from 'react'
import type { RoomState } from './reduceRoom'

export function Chat({ messages, onSend }: { messages: RoomState['chat']; onSend: (text: string) => void }) {
  const [text, setText] = useState('')

  function submit(e: FormEvent) {
    e.preventDefault()
    if (!text.trim()) return
    onSend(text.trim())
    setText('')
  }

  return (
    <section aria-label="Chat" className="chat">
      <ul className="chat-log" aria-live="polite">
        {messages.map((m, i) => (
          <li key={i}>
            <strong>{m.player}</strong> {m.text}
          </li>
        ))}
      </ul>
      <form onSubmit={submit} className="chat-form">
        <label htmlFor="chat-input" className="visually-hidden">Message</label>
        <input id="chat-input" value={text} onChange={e => setText(e.target.value)} maxLength={300} autoComplete="off" />
        <button type="submit">Send</button>
      </form>
    </section>
  )
}
