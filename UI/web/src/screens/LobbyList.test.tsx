import { act, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, beforeEach, expect, test, vi } from 'vitest'
import * as api from '../api'
import { room } from '../test-utils'
import { LobbyList, POLL_MS } from './LobbyList'

vi.mock('../api', async importOriginal => ({ ...(await importOriginal<typeof api>()), listRooms: vi.fn() }))
const listRooms = vi.mocked(api.listRooms)

// braces matter: a function returned from beforeEach runs as teardown, and mock methods return the mock
beforeEach(() => { listRooms.mockReset() })
afterEach(() => vi.useRealTimers())

test('lists rooms and only lobby-phase rooms can be joined', async () => {
  listRooms.mockResolvedValue([room(), room({ room_code: 'WXYZ', room_name: 'Busy', difficulty: 'hard', phase: 'question', players: ['a', 'b'] })])
  const onJoin = vi.fn()
  render(<LobbyList onJoin={onJoin} />)
  expect(await screen.findByText('Friday Trivia')).toBeTruthy()
  expect(screen.getByText('In progress')).toBeTruthy()
  expect(screen.getByText('2 players')).toBeTruthy()
  expect(screen.getByText(/· Hard$/)).toBeTruthy()
  const joins = screen.getAllByRole('button', { name: /join/i })
  expect(joins).toHaveLength(1)
  fireEvent.click(joins[0])
  expect(onJoin).toHaveBeenCalledWith('ABCD')
})

test('shows an empty state', async () => {
  listRooms.mockResolvedValue([])
  render(<LobbyList onJoin={() => {}} />)
  expect(await screen.findByText('No rooms yet')).toBeTruthy()
})

test('shows that the server is unreachable', async () => {
  listRooms.mockImplementation(async () => { throw new TypeError('Failed to fetch') })
  render(<LobbyList onJoin={() => {}} />)
  expect(await screen.findByText(/can't reach the server/i)).toBeTruthy()
})

test('polls while mounted and stops after unmount', async () => {
  vi.useFakeTimers()
  listRooms.mockResolvedValue([])
  const { unmount } = render(<LobbyList onJoin={() => {}} />)
  expect(listRooms).toHaveBeenCalledTimes(1)
  await act(() => vi.advanceTimersByTimeAsync(POLL_MS))
  expect(listRooms).toHaveBeenCalledTimes(2)
  unmount()
  await act(() => vi.advanceTimersByTimeAsync(POLL_MS * 3))
  expect(listRooms).toHaveBeenCalledTimes(2)
})
