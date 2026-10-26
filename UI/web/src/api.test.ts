import { afterEach, expect, test, vi } from 'vitest'
import { ApiError, createRoom, getRoom } from './api'

const respond = (status: number, body: unknown) =>
  vi.stubGlobal('fetch', vi.fn(async () => new Response(JSON.stringify(body), { status })))

afterEach(() => vi.unstubAllGlobals())

test('a 422 becomes an ApiError carrying the field and message', async () => {
  respond(422, { detail: [{ loc: ['body', 'topic'], msg: 'String should have at least 2 characters' }] })
  const error = await createRoom({ room_name: 'R', room_description: '', topic: 'x', mode: 'trivia' }).catch(e => e)
  expect(error).toBeInstanceOf(ApiError)
  expect(error.status).toBe(422)
  expect(error.message).toBe('topic: String should have at least 2 characters')
})

test('a 404 string detail is the message', async () => {
  respond(404, { detail: 'Room not found' })
  await expect(getRoom('ZZZZ')).rejects.toThrow('Room not found')
})
