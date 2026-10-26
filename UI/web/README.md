# Trivia web app

React + Vite + TypeScript front end for `../../trivia-backend`. Spec: [`../SPEC-frontend.md`](../SPEC-frontend.md).

## Run

Start the backend first (from `trivia-backend`): `uv run fastapi dev app/main.py`. It must be on
`http://localhost:8000`: the Vite dev server proxies `/rooms`, `/categories` and `/ws` to it (`vite.config.ts`).

```
npm install
npm run dev     # http://localhost:5173
npm test        # vitest, no backend needed
npm run build
npm run lint
```

To play with others on the same Wi-Fi, run `npm run dev -- --host` and share the `Network:` URL it prints
(`http://<your-LAN-IP>:5173`). Allow Node through Windows Firewall when asked (Private networks only).

Starting a game makes live LLM and Wikipedia calls on the backend (about 30 s, rate-limited).

## Layout

```
src/api.ts             REST calls + types mirroring trivia-backend/app/api/dto.py and the WS protocol
src/socket.ts          useRoomSocket: one WebSocket per room view, messages reduced by room/reduceRoom.ts
src/App.tsx            screen switch: home | create | join | room
src/screens/           Home, LobbyList (polls /rooms every 5 s), CreateRoom, JoinRoom, Room
src/room/              Lobby, Chat, Generating, Question, Results
src/test-utils.ts      room() fixture and FakeSocket for tests
```
