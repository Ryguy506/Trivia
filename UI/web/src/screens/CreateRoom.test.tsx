import { fireEvent, render, screen } from '@testing-library/react'
import { beforeEach, expect, test, vi } from 'vitest'
import * as api from '../api'
import { room } from '../test-utils'
import { CreateRoom } from './CreateRoom'

vi.mock('../api', async importOriginal => ({
  ...(await importOriginal<typeof api>()),
  createRoom: vi.fn(),
  listCategories: vi.fn(async () => ['History', 'Music']),
}))
const createRoom = vi.mocked(api.createRoom)
beforeEach(() => { createRoom.mockReset() })

function fill(fields: Record<string, string>) {
  for (const [label, value] of Object.entries(fields)) {
    fireEvent.change(screen.getByLabelText(label), { target: { value } })
  }
  fireEvent.click(screen.getByRole('button', { name: 'Create room' }))
}

test('blocks a too-short topic before sending', () => {
  render(<CreateRoom onCreated={() => {}} onBack={() => {}} />)
  fill({ 'Room name': 'Friday', Topic: ' x ', 'Your name': 'ann' })
  expect(screen.getByRole('alert').textContent).toMatch(/topic/i)
  expect(createRoom).not.toHaveBeenCalled()
})

test('shows a server 422', async () => {
  createRoom.mockImplementation(async () => { throw new api.ApiError(422, [{ loc: ['body', 'topic'], msg: 'bad topic' }]) })
  render(<CreateRoom onCreated={() => {}} onBack={() => {}} />)
  fill({ 'Room name': 'Friday', Topic: 'Volcanoes', 'Your name': 'ann' })
  expect((await screen.findByRole('alert')).textContent).toBe('topic: bad topic')
})

test('sends trivia mode and hands back the room and trimmed name', async () => {
  createRoom.mockResolvedValue(room())
  const onCreated = vi.fn()
  render(<CreateRoom onCreated={onCreated} onBack={() => {}} />)
  fill({ 'Room name': 'Friday', Topic: 'Volcanoes', 'Your name': ' ann ' })
  await vi.waitFor(() => expect(onCreated).toHaveBeenCalledWith(room(), 'ann'))
  expect(createRoom).toHaveBeenCalledWith({ room_name: 'Friday', room_description: '', topic: 'Volcanoes', mode: 'trivia' })
})
