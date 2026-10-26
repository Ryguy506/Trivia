import { useEffect, useState } from 'react'
import type { QuestionMessage } from './reduceRoom'

const secondsLeft = (deadline: number) => Math.max(0, Math.ceil((deadline - Date.now()) / 1000))

// Render with key={question.index}: a new question remounts this and unlocks the buttons
export function Question({ question, onAnswer }: { question: QuestionMessage; onAnswer: (index: number) => void }) {
  const [chosen, setChosen] = useState<number | null>(null)
  // The server owns the real deadline; this only draws it, counted from when the question arrived
  const [deadline] = useState(() => Date.now() + question.seconds * 1000)
  const [left, setLeft] = useState(question.seconds)

  useEffect(() => {
    const id = setInterval(() => setLeft(secondsLeft(deadline)), 250)
    return () => clearInterval(id)
  }, [deadline])

  const timeUp = left === 0
  function answer(index: number) {
    if (chosen !== null || timeUp) return // the server keeps only the first answer anyway
    setChosen(index)
    onAnswer(index)
  }

  return (
    <section aria-label="Question" className="question">
      <div className="question-meta">
        <p className="muted">Question {question.index + 1} of {question.total}</p>
        <p role="timer" aria-label="Time left" className={left <= 5 ? 'timer urgent' : 'timer'}>{left}s</p>
      </div>
      <h2>{question.question}</h2>
      <div className="options">
        {question.options.map((text, i) => (
          <button
            key={i}
            className={i === chosen ? 'option chosen' : 'option'}
            disabled={chosen !== null || timeUp}
            aria-pressed={i === chosen}
            onClick={() => answer(i)}
          >
            {'ABCD'[i]}. {text}
          </button>
        ))}
      </div>
      {chosen !== null && <p className="muted">Answer locked in. Waiting for everyone else…</p>}
      {chosen === null && timeUp && <p className="muted">Time's up. Waiting for the next question…</p>}
    </section>
  )
}
