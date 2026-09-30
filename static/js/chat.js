let chatWs = null;

function connectSession() {
  const player = document.getElementById("player-select").value;
  const lang = document.getElementById("lang-select").value;

  const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
  const wsUrl = `${protocol}//${window.location.host}/ws/${player}/${lang}`;

  chatWs = new WebSocket(wsUrl);

  chatWs.onopen = () => {
    document.getElementById("btn-connect").disabled = true;
    document.getElementById("player-select").disabled = true;
    document.getElementById("lang-select").disabled = true;

    document.getElementById("chat-input").disabled = false;
    document.getElementById("btn-send").disabled = false;
    document.getElementById("target-lang-tag").innerText = `My Lang: ${lang.toUpperCase()}`;
  };

  chatWs.onmessage = (event) => {
    const data = JSON.parse(event.data);
    const feed = document.getElementById("chat-feed");

    if (data.type === "assigned_role") {
      mySymbol = data.symbol;
      const roleBadge = document.getElementById("player-badge");
      roleBadge.innerText = `You: ${data.player_id} (${mySymbol})`;
      roleBadge.className = "badge-role active";
    }
    else if (data.type === "game_state") {
      syncGameState(data);
    }
    else if (data.type === "game_error") {
      showBannerWarning(data.message);
    }
    else if (data.type === "chat_alert") {
      const alertDiv = document.createElement("div");
      alertDiv.className = "blocked-card";
      alertDiv.innerText = data.text;
      feed.appendChild(alertDiv);
      feed.scrollTop = feed.scrollHeight;
    }
    else if (data.type === "chat_ack") {
      const bubble = document.createElement("div");
      bubble.className = "msg-bubble sent";
      bubble.innerHTML = `<div>${escapeHtml(data.text)}</div>`;
      feed.appendChild(bubble);
      feed.scrollTop = feed.scrollHeight;
    }
    else if (data.type === "chat_incoming") {
      const bubble = document.createElement("div");
      bubble.className = "msg-bubble received";

      const tagClass = data.verdict === "TOXIC" ? "meta-tag toxic" : "meta-tag clean";
      const tagText = data.verdict === "TOXIC" ? "⚠️ Toxic (Warned)" : "✓ Clean";

      bubble.innerHTML = `
        <div class="${tagClass}">${tagText}</div>
        <div style="font-size: 15px; font-weight: 600; margin-bottom: 2px;">${escapeHtml(data.translated)}</div>
        <div style="font-size: 11px; color: var(--text-dim);">${data.sender}: <em>"${escapeHtml(data.original)}"</em></div>
      `;
      feed.appendChild(bubble);
      feed.scrollTop = feed.scrollHeight;
    }
  };

  const input = document.getElementById("chat-input");
  input.onkeydown = (e) => {
    if (e.key === "Enter") sendChatMessage();
  };
}

function sendChatMessage() {
  const input = document.getElementById("chat-input");
  const msg = input.value.trim();
  if (!msg || !chatWs) return;

  chatWs.send(JSON.stringify({ type: "chat", text: msg }));
  input.value = "";
}

function escapeHtml(text) {
  const div = document.createElement("div");
  div.innerText = text;
  return div.innerHTML;
}