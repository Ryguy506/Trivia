import { useEffect, useState } from 'react'
import type { QuestionMessage, RoundResult } from './reduceRoom'

const secondsLeft = (deadline: number) => Math.max(0, Math.ceil((deadline - Date.now()) / 1000))

interface Props {
  question: QuestionMessage
  reveal?: RoundResult | null // set once the round ends: shows the right answer and its source
  onAnswer: (index: number) => void
}

function optionClass(i: number, chosen: number | null, reveal: RoundResult | null | undefined) {
  if (reveal && i === reveal.correct_index) return 'option correct'
  if (reveal && i === chosen) return 'option wrong'
  return i === chosen ? 'option chosen' : 'option'
}

// Render with key={question.index}: a new question remounts this and unlocks the buttons
export function Question({ question, reveal, onAnswer }: Props) {
  const [chosen, setChosen] = useState<number | null>(null)
  // The server owns the real deadline; this only draws it, counted from when the question arrived
  const [deadline] = useState(() => Date.now() + question.seconds * 1000)
  const [left, setLeft] = useState(question.seconds)

  useEffect(() => {
    const id = setInterval(() => setLeft(secondsLeft(deadline)), 250)
    return () => clearInterval(id)
  }, [deadline])

  const timeUp = left === 0
  const locked = chosen !== null || timeUp || !!reveal
  function answer(index: number) {
    if (locked) return // the server keeps only the first answer anyway
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
            className={optionClass(i, chosen, reveal)}
            disabled={locked}
            aria-pressed={i === chosen}
            onClick={() => answer(i)}
          >
            {'ABCD'[i]}. {text}
          </button>
        ))}
      </div>
      {reveal ? (
        <div className="reveal">
          <p role="status">
            {chosen === reveal.correct_index
              ? 'Correct!'
              : `${chosen === null ? 'No answer' : 'Wrong'}. The answer was ${'ABCD'[reveal.correct_index]}. ${question.options[reveal.correct_index]}`}
          </p>
          <blockquote>{reveal.supporting_quote}</blockquote>
          <a href={reveal.source_url} target="_blank" rel="noreferrer">Source</a>
        </div>
      ) : (
        <>
          {chosen !== null && <p className="muted">Answer locked in. Waiting for everyone else…</p>}
          {chosen === null && timeUp && <p className="muted">Time's up. Waiting for the next question…</p>}
        </>
      )}
    </section>
  )
}
