import { act, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, beforeEach, expect, test, vi } from 'vitest'
import { Question } from './Question'
import type { QuestionMessage, RoundResult } from './reduceRoom'

const question: QuestionMessage = { type: 'question', index: 0, total: 5, question: 'Q?', options: ['A1', 'B1', 'C1', 'D1'], seconds: 30 }

beforeEach(() => { vi.useFakeTimers() })
afterEach(() => { vi.useRealTimers() })

test('counts down from the server seconds and locks the answers at zero', () => {
  const onAnswer = vi.fn()
  render(<Question question={question} onAnswer={onAnswer} />)
  expect(screen.getByRole('timer').textContent).toBe('30s')

  act(() => { vi.advanceTimersByTime(10_000) })
  expect(screen.getByRole('timer').textContent).toBe('20s')

  act(() => { vi.advanceTimersByTime(20_000) })
  expect(screen.getByRole('timer').textContent).toBe('0s')
  fireEvent.click(screen.getByRole('button', { name: /A1/ }))
  expect(onAnswer).not.toHaveBeenCalled()
  expect(screen.getByText(/Time's up/)).toBeTruthy()
})

const reveal: RoundResult = { type: 'round_result', index: 0, correct_index: 2, supporting_quote: 'C1 is the answer.',
                              source_url: 'https://en.wikipedia.org/wiki/C1', scores: {} }

test('the reveal marks a wrong pick and the right answer, with the quote and source', () => {
  const { rerender } = render(<Question question={question} onAnswer={() => {}} />)
  fireEvent.click(screen.getByRole('button', { name: /B1/ }))
  rerender(<Question question={question} reveal={reveal} onAnswer={() => {}} />)

  expect(screen.getByRole('status').textContent).toBe('Wrong. The answer was C. C1')
  expect(screen.getByRole('button', { name: /C1/ }).className).toContain('correct')
  expect(screen.getByRole('button', { name: /B1/ }).className).toContain('wrong')
  expect(screen.getByText('C1 is the answer.')).toBeTruthy()
  const link = screen.getByRole('link', { name: 'Source' }) as HTMLAnchorElement
  expect(link.href).toBe('https://en.wikipedia.org/wiki/C1')
  expect(link.target).toBe('_blank')
  for (const b of screen.getAllByRole('button')) expect((b as HTMLButtonElement).disabled).toBe(true)
})

test('the reveal says correct for a right pick and names the answer when there was no pick', () => {
  const { rerender, unmount } = render(<Question question={question} onAnswer={() => {}} />)
  fireEvent.click(screen.getByRole('button', { name: /C1/ }))
  rerender(<Question question={question} reveal={reveal} onAnswer={() => {}} />)
  expect(screen.getByRole('status').textContent).toBe('Correct!')
  unmount()

  render(<Question question={question} reveal={reveal} onAnswer={() => {}} />)
  expect(screen.getByRole('status').textContent).toBe('No answer. The answer was C. C1')
})
