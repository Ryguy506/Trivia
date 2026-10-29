import type { Phase, ServerMessage } from '../api'

export type QuestionMessage = Extract<ServerMessage, { type: 'question' }>
export type RoundResult = Extract<ServerMessage, { type: 'round_result' }>

export interface RoomState {
  phase: Phase
  players: string[]
  host: string | null // learned from our own player_joined; only the host can start
  chat: { player: string; text: string }[]
  question: QuestionMessage | null
  reveal: RoundResult | null // the answer to the current question, between its round end and the next question
  scores: Record<string, number> | null
  error: string | null
}

export const initialRoom = (players: string[], phase: Phase): RoomState =>
  ({ phase, players, host: null, chat: [], question: null, reveal: null, scores: null, error: null })

export function reduceRoom(state: RoomState, msg: ServerMessage): RoomState {
  switch (msg.type) {
    case 'player_joined':
    case 'player_left':
      return { ...state, players: msg.players, host: msg.host }
    case 'chat':
      return { ...state, chat: [...state.chat, { player: msg.player, text: msg.text }] }
    case 'phase':
      // an error from the last attempt stays visible in the lobby until the next start
      return { ...state, phase: msg.phase, error: msg.phase === 'generating' ? null : state.error }
    case 'question':
      return { ...state, question: msg, reveal: null }
    case 'round_result':
      return { ...state, reveal: msg }
    case 'results':
      return { ...state, scores: msg.scores }
    case 'error':
      return { ...state, error: msg.message }
    default:
      return state // unknown message types from a newer server are ignored
  }
}
