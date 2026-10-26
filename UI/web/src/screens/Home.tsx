import { LobbyList } from './LobbyList'

interface Props {
  onCreate: () => void
  onJoin: (code?: string) => void
}

export function Home({ onCreate, onJoin }: Props) {
  return (
    <main>
      <h1>Trivia</h1>
      <div className="actions">
        <button className="primary" onClick={onCreate}>Create room</button>
        <button onClick={() => onJoin()}>Join with code</button>
      </div>
      <LobbyList onJoin={onJoin} />
    </main>
  )
}
