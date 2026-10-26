import { useCallback, useEffect, useReducer, useRef, useState } from 'react'
import { WS_URL, type RoomOut, type ServerMessage } from './api'
import { initialRoom, reduceRoom } from './room/reduceRoom'

export type ClientMessage =
  | { type: 'start_game' }
  | { type: 'chat'; text: string }
  | { type: 'submit_answer'; answer_index: number }

export function useRoomSocket(room: RoomOut, player: string) {
  const [state, dispatch] = useReducer(reduceRoom, undefined, () => initialRoom(room.players, room.phase))
  const [closeCode, setCloseCode] = useState<number | null>(null)
  const socketRef = useRef<WebSocket | null>(null)
  const { room_code } = room

  useEffect(() => {
    let socket: WebSocket | null = null
    // Connect on the next tick: StrictMode's mount → unmount → mount clears this timer first, so only one
    // socket opens. Two sockets with one name would race on the server and one would get closed with 4009.
    const timer = setTimeout(() => {
      socket = new WebSocket(`${WS_URL}/ws/${encodeURIComponent(room_code)}/${encodeURIComponent(player)}`)
      socketRef.current = socket
      socket.onmessage = e => {
        try {
          dispatch(JSON.parse(e.data) as ServerMessage)
        } catch {
          // skip malformed frames
        }
      }
      socket.onclose = e => setCloseCode(e.code)
    }, 0)
    return () => {
      clearTimeout(timer)
      if (socket) {
        socket.onclose = null
        socket.close()
      }
      socketRef.current = null
    }
  }, [room_code, player])

  const send = useCallback((message: ClientMessage) => {
    const socket = socketRef.current
    if (socket?.readyState === WebSocket.OPEN) socket.send(JSON.stringify(message))
  }, [])

  return { state, closeCode, send }
}
