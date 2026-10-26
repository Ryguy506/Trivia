import { expect, test } from 'vitest'
import { initialRoom, reduceRoom } from './reduceRoom'

test('player list follows joins and leaves', () => {
  let state = initialRoom(['ann'], 'lobby')
  state = reduceRoom(state, { type: 'player_joined', player: 'bob', players: ['ann', 'bob'] })
  expect(state.players).toEqual(['ann', 'bob'])
  state = reduceRoom(state, { type: 'player_left', player: 'ann', players: ['bob'] })
  expect(state.players).toEqual(['bob'])
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
