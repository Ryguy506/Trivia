import { act, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, beforeEach, expect, test, vi } from 'vitest'
import { Question } from './Question'
import type { QuestionMessage } from './reduceRoom'

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
