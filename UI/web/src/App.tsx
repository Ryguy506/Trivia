import { useState } from 'react'
import type { RoomOut } from './api'
import { CreateRoom } from './screens/CreateRoom'
import { Home } from './screens/Home'
import { JoinRoom } from './screens/JoinRoom'
import { Room } from './screens/Room'

type Screen =
  | { name: 'home' }
  | { name: 'create' }
  | { name: 'join'; code?: string }
  | { name: 'room'; room: RoomOut; player: string }

export default function App() {
  const [screen, setScreen] = useState<Screen>({ name: 'home' })
  const home = () => setScreen({ name: 'home' })
  const enter = (room: RoomOut, player: string) => setScreen({ name: 'room', room, player })

  switch (screen.name) {
    case 'home':
      return <Home onCreate={() => setScreen({ name: 'create' })} onJoin={code => setScreen({ name: 'join', code })} />
    case 'create':
      return <CreateRoom onCreated={enter} onBack={home} />
    case 'join':
      return <JoinRoom code={screen.code} onJoined={enter} onBack={home} />
    case 'room':
      return <Room key={`${screen.room.room_code}/${screen.player}`} room={screen.room} player={screen.player} onLeave={home} />
  }
}
