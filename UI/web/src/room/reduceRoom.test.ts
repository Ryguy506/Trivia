import { expect, test } from 'vitest'
import { initialRoom, reduceRoom } from './reduceRoom'

test('player list and host follow joins and leaves', () => {
  let state = initialRoom(['ann'], 'lobby')
  expect(state.host).toBeNull()
  state = reduceRoom(state, { type: 'player_joined', player: 'bob', players: ['ann', 'bob'], host: 'ann' })
  expect(state).toMatchObject({ players: ['ann', 'bob'], host: 'ann' })
  state = reduceRoom(state, { type: 'player_left', player: 'ann', players: ['bob'], host: 'bob' })
  expect(state).toMatchObject({ players: ['bob'], host: 'bob' })
})

test('chat messages are appended in order', () => {
  let state = initialRoom([], 'lobby')
  state = reduceRoom(state, { type: 'chat', player: 'ann', text: 'hi' })
  state = reduceRoom(state, { type: 'chat', player: 'bob', text: 'yo' })
  expect(state.chat).toEqual([{ player: 'ann', text: 'hi' }, { player: 'bob', text: 'yo' }])
})

test('a failed generation keeps its error in the lobby until the next start', () => {
  let state = initialRoom([], 'lobby')
  state = reduceRoom(state, { type: 'phase', phase: 'generating' })
  state = reduceRoom(state, { type: 'error', message: 'Not enough material' })
  state = reduceRoom(state, { type: 'phase', phase: 'lobby' })
  expect(state).toMatchObject({ phase: 'lobby', error: 'Not enough material' })
  state = reduceRoom(state, { type: 'phase', phase: 'generating' })
  expect(state.error).toBeNull()
})

test('a round result shows until the next question', () => {
  const result = { type: 'round_result', index: 0, correct_index: 2, supporting_quote: 'It is C.',
                   source_url: 'https://example.com', scores: { ann: 1 } } as const
  let state = initialRoom(['ann'], 'question')
  state = reduceRoom(state, result)
  expect(state.reveal).toEqual(result)
  state = reduceRoom(state, { type: 'question', index: 1, total: 2, question: 'Q?', options: ['a', 'b', 'c', 'd'], seconds: 30 })
  expect(state.reveal).toBeNull()
})
