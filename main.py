import json
from typing import Dict, Optional
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from core.classifier import GeminiModerator

app = FastAPI(title="Gemini Game Moderation")
app.mount("/static", StaticFiles(directory="static"), name="static")

WIN_PATTERNS = [
    [0, 1, 2], [3, 4, 5], [6, 7, 8],  # Rows
    [0, 3, 6], [1, 4, 7], [2, 5, 8],  # Columns
    [0, 4, 8], [2, 4, 6]              # Diagonals
]

class GameState:
    def __init__(self):
        self.players: Dict[str, dict] = {}  # "Player1", "Player2"
        self.board = ["" for _ in range(9)]
        self.current_turn = "X"
        self.winner: Optional[str] = None
        self.is_draw = False

    def check_winner(self):
        for a, b, c in WIN_PATTERNS:
            if self.board[a] and self.board[a] == self.board[b] == self.board[c]:
                self.winner = self.board[a]
                return self.winner
        if all(cell != "" for cell in self.board):
            self.is_draw = True
            return "DRAW"
        return None

    def reset(self):
        self.board = ["" for _ in range(9)]
        self.current_turn = "X"
        self.winner = None
        self.is_draw = False

game = GameState()

async def broadcast_state():
    payload = json.dumps({
        "type": "game_state",
        "board": game.board,
        "current_turn": game.current_turn,
        "winner": game.winner,
        "is_draw": game.is_draw,
        "player_count": len(game.players)
    })
    for p in list(game.players.values()):
        try:
            await p["ws"].send_text(payload)
        except Exception:
            pass

@app.get("/")
def serve_index():
    with open("templates/index.html", "r", encoding="utf-8") as f:
        return HTMLResponse(f.read())

@app.websocket("/ws/{player_id}/{lang}")
async def websocket_handler(ws: WebSocket, player_id: str, lang: str):
    await ws.accept()

    # Deterministic symbol mapping
    symbol = "X" if "1" in player_id else "O"
    game.players[player_id] = {
        "ws": ws,
        "lang": lang,
        "symbol": symbol
    }

    print(f"\n[CONNECTED] {player_id} as '{symbol}' (Target lang: {lang})")

    # Inform player of their symbol
    await ws.send_text(json.dumps({
        "type": "assigned_role",
        "symbol": symbol,
        "player_id": player_id
    }))

    # Sync state across both players
    await broadcast_state()

    try:
        while True:
            raw = await ws.receive_text()
            data = json.loads(raw)
            event_type = data.get("type")

            # ---------------------------
            # 1. MOVE EVENT
            # ---------------------------
            if event_type == "move":
                idx = data.get("index")

                # If game ended, ignore moves
                if game.winner or game.is_draw:
                    continue

                # Strict turn validation
                if symbol != game.current_turn:
                    await ws.send_text(json.dumps({
                        "type": "game_error",
                        "message": f"Wait! It is Player {game.current_turn}'s turn."
                    }))
                    continue

                # Cell empty validation
                if 0 <= idx < 9 and game.board[idx] == "":
                    game.board[idx] = symbol
                    outcome = game.check_winner()

                    if not outcome:
                        game.current_turn = "O" if game.current_turn == "X" else "X"

                    await broadcast_state()

            # ---------------------------
            # 2. RESET EVENT
            # ---------------------------
            elif event_type == "reset":
                game.reset()
                await broadcast_state()

            # --- 3. CHAT EVENT (VIA GEMINI) ---
            elif event_type == "chat":
                msg = data.get("text", "").strip()
                if not msg:
                    continue

                # Map code to full language name so Gemini translates accurately
                LANG_NAMES = {
                    "en": "English",
                    "hi": "Hindi (written in Devanagari script)",
                    "ta": "Tamil (written in Tamil script)",
                    "te": "Telugu (written in Telugu script)",
                    "es": "Spanish"
                }

                # Find opponent's target language
                opponent_lang_code = "en"
                for pid, pdata in game.players.items():
                    if pid != player_id:
                        opponent_lang_code = pdata["lang"]

                target_lang_name = LANG_NAMES.get(opponent_lang_code, "English")

                # Process through Gemini AI
                result = GeminiModerator.process_chat(msg, target_lang_name)
                verdict = result["verdict"]

                print(f"[CHAT ROUTE] From: {player_id} -> Target: {target_lang_name} | Verdict: {verdict}")

                # HARASSMENT -> HARD BLOCK
                if verdict == "HARASSMENT":
                    await ws.send_text(json.dumps({
                        "type": "chat_alert",
                        "text": f"🚫 Message blocked! Flagged as Harassment ({result.get('reason', 'Policy Violation')})."
                    }))
                    continue

                # Sender sees their sent bubble
                await ws.send_text(json.dumps({
                    "type": "chat_ack",
                    "text": msg,
                    "verdict": verdict
                }))

                # Opponent sees the translated & moderated message
                for pid, pdata in list(game.players.items()):
                    if pid != player_id:
                        await pdata["ws"].send_text(json.dumps({
                            "type": "chat_incoming",
                            "sender": player_id,
                            "original": msg,
                            "translated": result["translated"],
                            "verdict": verdict,
                            "lang": result.get("detected_lang", "")
                        }))

    except WebSocketDisconnect:
        print(f"[DISCONNECT] {player_id} left.")
        if player_id in game.players:
            del game.players[player_id]
        await broadcast_state()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000, reload=False)