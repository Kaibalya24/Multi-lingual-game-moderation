let mySymbol = null;
let currentTurn = "X";
let isGameFinished = false;

window.addEventListener("DOMContentLoaded", () => {
  document.querySelectorAll(".cell").forEach((cell) => {
    cell.addEventListener("click", () => {
      const idx = parseInt(cell.getAttribute("data-idx"));
      handleCellClick(idx);
    });
  });
});

function handleCellClick(index) {
  if (!chatWs || isGameFinished) return;

  if (mySymbol !== currentTurn) {
    showBannerWarning(`Wait! It is Player ${currentTurn}'s turn.`);
    return;
  }

  chatWs.send(JSON.stringify({
    type: "move",
    index: index
  }));
}

function syncGameState(data) {
  currentTurn = data.current_turn;
  const turnBanner = document.getElementById("turn-banner");

  data.board.forEach((val, i) => {
    const cell = document.querySelector(`.cell[data-idx="${i}"]`);
    if (cell) {
      cell.innerText = val;
      cell.className = "cell";
      if (val === "X") cell.classList.add("x");
      if (val === "O") cell.classList.add("o");
    }
  });

  if (data.winner) {
    isGameFinished = true;
    const isWinner = data.winner === mySymbol;
    turnBanner.innerText = isWinner ? "🏆 YOU WON!" : `💀 PLAYER ${data.winner} WON!`;
    turnBanner.style.color = isWinner ? "#10b981" : "#ef4444";
  } else if (data.is_draw) {
    isGameFinished = true;
    turnBanner.innerText = "🤝 MATCH DRAW!";
    turnBanner.style.color = "#f59e0b";
  } else {
    isGameFinished = false;
    const isMyTurn = mySymbol === currentTurn;
    turnBanner.innerText = isMyTurn ? `👉 YOUR TURN (${mySymbol})` : `⏳ Player ${currentTurn}'s Turn...`;
    turnBanner.style.color = isMyTurn ? "#38bdf8" : "#94a3b8";
  }
}

function triggerReset() {
  if (chatWs) {
    chatWs.send(JSON.stringify({ type: "reset" }));
  }
}

function showBannerWarning(msg) {
  const banner = document.getElementById("turn-banner");
  const oldText = banner.innerText;
  const oldColor = banner.style.color;
  banner.innerText = msg;
  banner.style.color = "#ef4444";
  setTimeout(() => {
    banner.innerText = oldText;
    banner.style.color = oldColor;
  }, 1600);
}