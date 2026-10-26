import type { RoomOut } from './api'

export const room = (overrides: Partial<RoomOut> = {}): RoomOut => ({
  room_code: 'ABCD',
  room_name: 'Friday Trivia',
  room_description: '',
  topic: 'Volcanoes',
  mode: 'trivia',
  phase: 'lobby',
  players: ['ann'],
  ...overrides,
})

// Stands in for the browser WebSocket: tests open it, push server messages and read what was sent
export class FakeSocket {
  static instances: FakeSocket[] = []
  static readonly OPEN = 1
  url: string
  readyState = 0
  sent: unknown[] = []
  onopen: (() => void) | null = null
  onmessage: ((e: { data: string }) => void) | null = null
  onclose: ((e: { code: number }) => void) | null = null

  constructor(url: string) {
    this.url = url
    FakeSocket.instances.push(this)
  }

  send(data: string) { this.sent.push(JSON.parse(data)) }
  close() { this.readyState = 3 }

  // test helpers
  open() { this.readyState = 1; this.onopen?.() }
  receive(message: unknown) { this.onmessage?.({ data: JSON.stringify(message) }) }
  serverClose(code: number) { this.readyState = 3; this.onclose?.({ code }) }
  static last() { return FakeSocket.instances[FakeSocket.instances.length - 1] }
}
