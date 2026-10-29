// Types mirror trivia-backend/app/api/dto.py and the WebSocket protocol in its CLAUDE.md.
// Relative: the Vite dev server proxies these to the backend (vite.config.ts)
export const API_URL = ''
export const WS_URL = `${location.protocol === 'https:' ? 'wss' : 'ws'}://${location.host}`

export type Mode = 'trivia'
export type Difficulty = 'easy' | 'medium' | 'hard'
export const difficultyLabel: Record<Difficulty, string> = { easy: 'Easy', medium: 'Medium', hard: 'Hard' }
export type Phase = 'lobby' | 'generating' | 'question' | 'results'

export interface RoomCreate {
  room_name: string
  room_description: string
  topic: string
  mode: Mode
  difficulty: Difficulty
}

export interface RoomOut {
  room_code: string
  room_name: string
  room_description: string
  topic: string
  mode: Mode
  difficulty: Difficulty
  phase: Phase
  players: string[]
}

export type ServerMessage =
  | { type: 'player_joined' | 'player_left'; player: string; players: string[]; host: string | null }
  | { type: 'chat'; player: string; text: string }
  | { type: 'phase'; phase: Phase }
  | { type: 'question'; index: number; total: number; question: string; options: string[]; seconds: number }
  | { type: 'round_result'; index: number; correct_index: number; supporting_quote: string; source_url: string; scores: Record<string, number> }
  | { type: 'results'; scores: Record<string, number> }
  | { type: 'error'; message: string }

export class ApiError extends Error {
  status: number
  detail: unknown

  constructor(status: number, detail: unknown) {
    super(describeDetail(detail) || `Request failed (${status})`)
    this.status = status
    this.detail = detail
  }
}

// FastAPI sends a string (404) or a list of {loc, msg} (422)
function describeDetail(detail: unknown): string {
  if (typeof detail === 'string') return detail
  if (Array.isArray(detail)) {
    return detail.map((d: { loc?: unknown[]; msg?: string }) => `${d.loc?.at(-1) ?? 'request'}: ${d.msg}`).join('; ')
  }
  return ''
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(API_URL + path, init)
  const body = await res.json().catch(() => null)
  if (!res.ok) throw new ApiError(res.status, body?.detail)
  return body as T
}

export const listRooms = () => request<RoomOut[]>('/rooms')
export const getRoom = (code: string) => request<RoomOut>(`/rooms/${encodeURIComponent(code)}`)
export const listCategories = () => request<string[]>('/categories')
export const createRoom = (body: RoomCreate) =>
  request<RoomOut>('/rooms', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
