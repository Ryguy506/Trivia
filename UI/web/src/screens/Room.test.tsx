import { StrictMode } from 'react'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { act } from 'react'
import { afterEach, beforeEach, expect, test, vi } from 'vitest'
import { FakeSocket, room } from '../test-utils'
import { Room } from './Room'

beforeEach(() => {
  FakeSocket.instances = []
  vi.stubGlobal('WebSocket', FakeSocket)
})
afterEach(() => { vi.unstubAllGlobals() })

async function enter(ui = <Room room={room()} player="ann" onLeave={() => {}} />) {
  render(ui)
  await waitFor(() => expect(FakeSocket.instances).toHaveLength(1))
  const socket = FakeSocket.last()
  act(() => socket.open())
  return socket
}

test('connects as the player and shows room info', async () => {
  const socket = await enter()
  expect(socket.url).toBe(`ws://${location.host}/ws/ABCD/ann`)
  expect(screen.getByText('Friday Trivia')).toBeTruthy()
  expect(screen.getByText('ABCD')).toBeTruthy()
  expect(screen.getByText('Trivia · Volcanoes · Medium')).toBeTruthy()
})

test('opens one socket even under StrictMode', async () => {
  await enter(<StrictMode><Room room={room()} player="ann" onLeave={() => {}} /></StrictMode>)
  await new Promise(r => setTimeout(r, 20))
  expect(FakeSocket.instances).toHaveLength(1)
})

test('player list and chat update from the socket; chat is plain text', async () => {
  const socket = await enter()
  act(() => socket.receive({ type: 'player_joined', player: 'bob', players: ['ann', 'bob'] }))
  expect(screen.getByText('bob')).toBeTruthy()
  act(() => socket.receive({ type: 'chat', player: 'bob', text: '<b>x</b>' }))
  expect(screen.getByText('<b>x</b>')).toBeTruthy()
})

test('sending chat writes a chat message to the socket', async () => {
  const socket = await enter()
  fireEvent.change(screen.getByLabelText('Message'), { target: { value: 'hello' } })
  fireEvent.click(screen.getByRole('button', { name: 'Send' }))
  expect(socket.sent).toEqual([{ type: 'chat', text: 'hello' }])
})

test.each([
  [4004, 'Room not found'],
  [4009, 'That name is taken in this room'],
  [1006, 'Disconnected'],
])('server close %i shows "%s" with a way home', async (code, message) => {
  const onLeave = vi.fn()
  const socket = await enter(<Room room={room()} player="ann" onLeave={onLeave} />)
  act(() => socket.serverClose(code))
  expect(screen.getByRole('alert').textContent).toBe(message)
  fireEvent.click(screen.getByRole('button', { name: 'Back to home' }))
  expect(onLeave).toHaveBeenCalled()
})

test('start → generating → error → lobby shows the error and lets you start again', async () => {
  const socket = await enter()
  fireEvent.click(screen.getByRole('button', { name: 'Start game' }))
  expect(socket.sent).toEqual([{ type: 'start_game' }])
  act(() => socket.receive({ type: 'phase', phase: 'generating' }))
  expect(screen.getByText('Generating questions…')).toBeTruthy()
  expect(screen.queryByRole('button', { name: 'Start game' })).toBeNull()
  act(() => {
    socket.receive({ type: 'error', message: 'Not enough material for that topic. Try something broader.' })
    socket.receive({ type: 'phase', phase: 'lobby' })
  })
  expect(screen.getByRole('alert').textContent).toMatch(/not enough material/i)
  expect((screen.getByRole('button', { name: 'Start game' }) as HTMLButtonElement).disabled).toBe(false)
})

const question = (index: number) =>
  ({ type: 'question', index, total: 2, question: `Question ${index}?`, options: ['Red', 'Green', 'Blue', 'Gold'], seconds: 30 })

test('a scripted game plays through questions to sorted results', async () => {
  const socket = await enter()
  act(() => {
    socket.receive({ type: 'phase', phase: 'question' })
    socket.receive(question(0))
  })
  expect(screen.getByText('Question 1 of 2')).toBeTruthy()
  fireEvent.click(screen.getByRole('button', { name: /Green/ }))
  fireEvent.click(screen.getByRole('button', { name: /Blue/ }))
  expect(socket.sent).toEqual([{ type: 'submit_answer', answer_index: 1 }])
  for (const b of screen.getAllByRole('button', { name: /^[A-D]\./ })) expect((b as HTMLButtonElement).disabled).toBe(true)

  act(() => socket.receive(question(1)))
  expect(screen.getByText('Question 2 of 2')).toBeTruthy()
  expect((screen.getByRole('button', { name: /Red/ }) as HTMLButtonElement).disabled).toBe(false)

  act(() => {
    socket.receive({ type: 'phase', phase: 'results' })
    socket.receive({ type: 'results', scores: { ann: 1, bob: 2, left_early: 0 } })
  })
  const rows = screen.getAllByRole('row').slice(1).map(r => r.textContent)
  expect(rows).toEqual(['bob2', 'ann1', 'left_early0'])
  expect(screen.getByRole('button', { name: 'Back to home' })).toBeTruthy()
})
