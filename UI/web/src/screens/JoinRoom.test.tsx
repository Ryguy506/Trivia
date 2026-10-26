import { fireEvent, render, screen } from '@testing-library/react'
import { beforeEach, expect, test, vi } from 'vitest'
import * as api from '../api'
import { room } from '../test-utils'
import { JoinRoom } from './JoinRoom'

vi.mock('../api', async importOriginal => ({ ...(await importOriginal<typeof api>()), getRoom: vi.fn() }))
const getRoom = vi.mocked(api.getRoom)
beforeEach(() => { getRoom.mockReset() })

function join(code: string | null, name: string) {
  if (code !== null) fireEvent.change(screen.getByLabelText('Room code'), { target: { value: code } })
  fireEvent.change(screen.getByLabelText('Your name'), { target: { value: name } })
  fireEvent.click(screen.getByRole('button', { name: 'Join' }))
}

test('an unknown code says the room was not found', async () => {
  getRoom.mockImplementation(async () => { throw new api.ApiError(404, 'Room not found') })
  render(<JoinRoom onJoined={() => {}} onBack={() => {}} />)
  join('zzzz', 'ann')
  expect((await screen.findByRole('alert')).textContent).toBe('Room not found')
})

test('a room mid-game cannot be joined', async () => {
  getRoom.mockResolvedValue(room({ phase: 'question' }))
  const onJoined = vi.fn()
  render(<JoinRoom onJoined={onJoined} onBack={() => {}} />)
  join('abcd', 'ann')
  expect((await screen.findByRole('alert')).textContent).toBe('Game in progress')
  expect(onJoined).not.toHaveBeenCalled()
})

test('the code is case-insensitive and the room is handed over', async () => {
  getRoom.mockResolvedValue(room())
  const onJoined = vi.fn()
  render(<JoinRoom onJoined={onJoined} onBack={() => {}} />)
  join(' abcd ', ' bob ')
  await vi.waitFor(() => expect(onJoined).toHaveBeenCalledWith(room(), 'bob'))
  expect(getRoom).toHaveBeenCalledWith('ABCD')
})

test('joining from the list pre-fills the code and only asks for a name', async () => {
  getRoom.mockResolvedValue(room())
  const onJoined = vi.fn()
  render(<JoinRoom code="ABCD" onJoined={onJoined} onBack={() => {}} />)
  expect(screen.queryByLabelText('Room code')).toBeNull()
  join(null, 'bob')
  await vi.waitFor(() => expect(onJoined).toHaveBeenCalled())
})
