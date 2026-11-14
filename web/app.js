/*
Created at: 2026-11-14 02:37 EST
Created by: Codex
Last Modified at: 2026-11-14 07:23 EST
Last Modified by: Codex
Resolves physical button semantics, calls the versioned API, and paints authoritative framebuffers.
*/

"use strict";

const state = {
  fireHeld: false,
  polling: false,
  lastSnapshot: null,
  lastEventKey: "",
  audioContext: null,
  clearPressed: false,
  clearLongCommitted: false,
  clearTimer: null,
};

const elements = {
  connection: document.querySelector("#connection"),
  connectionLabel: document.querySelector("#connection-label"),
  map: document.querySelector("#map-screen"),
  hud: document.querySelector("#hud-screen"),
  status: document.querySelector("#status"),
  tick: document.querySelector("#tick"),
  hash: document.querySelector("#hash"),
  fire: document.querySelector("#fire"),
  clear: document.querySelector("#clear"),
  pause: document.querySelector("#pause"),
  realtime: document.querySelector("#realtime"),
  step: document.querySelector("#step"),
  resetForm: document.querySelector("#reset-form"),
  seed: document.querySelector("#seed"),
};

function setConnection(mode, label) {
  elements.connection.dataset.state = mode;
  elements.connectionLabel.textContent = label;
}

function ensureAudio() {
  const AudioContext = window.AudioContext || window.webkitAudioContext;
  if (!AudioContext) return;
  if (!state.audioContext) state.audioContext = new AudioContext();
  if (state.audioContext.state === "suspended") {
    state.audioContext.resume().catch(() => {});
  }
}

function scheduleBeeps(pulses) {
  const context = state.audioContext;
  if (!context || context.state !== "running") return;
  const start = context.currentTime + 0.01;
  pulses.forEach(([offset, duration]) => {
    const oscillator = context.createOscillator();
    const gain = context.createGain();
    oscillator.type = "square";
    oscillator.frequency.value = 880;
    gain.gain.value = 0.035;
    oscillator.connect(gain);
    gain.connect(context.destination);
    oscillator.start(start + offset);
    oscillator.stop(start + offset + duration);
  });
}

function playObservableEvents(snapshot) {
  const events = Array.isArray(snapshot.last_events) ? snapshot.last_events : [];
  const key = `${snapshot.seed}:${snapshot.tick}:${JSON.stringify(events)}`;
  if (key === state.lastEventKey) return;
  state.lastEventKey = key;
  const types = new Set(events.map((event) => event.type));
  if (types.has("PLAYER_DEATH")) {
    scheduleBeeps([[0, 0.45]]);
  } else if (types.has("PLAYER_VICTORY")) {
    scheduleBeeps([[0, 0.07], [0.13, 0.07], [0.26, 0.1]]);
  } else if (types.has("PLAYER_DAMAGE")) {
    scheduleBeeps([[0, 0.08], [0.17, 0.08]]);
  } else if (types.has("ENEMY_SHOT_HEARD")) {
    scheduleBeeps([[0, 0.045], [0.1, 0.045]]);
  } else if (types.has("PLAYER_SHOT")) {
    scheduleBeeps([[0, 0.07]]);
  }
}

async function api(path, options = {}) {
  const response = await fetch(path, {
    cache: "no-store",
    ...options,
    headers: options.body ? { "Content-Type": "application/json" } : undefined,
  });
  if (!response.ok) {
    const body = await response.text();
    throw new Error(`${response.status} ${body}`);
  }
  return response.json();
}

function paint(canvas, hex) {
  if (typeof hex !== "string" || hex.length !== 2048) {
    throw new Error("invalid 128x64 framebuffer payload");
  }
  const context = canvas.getContext("2d", { alpha: false });
  const image = context.createImageData(128, 64);
  for (let y = 0; y < 64; y += 1) {
    for (let x = 0; x < 128; x += 1) {
      const byteIndex = x + Math.floor(y / 8) * 128;
      const byte = Number.parseInt(hex.slice(byteIndex * 2, byteIndex * 2 + 2), 16);
      const on = (byte & (1 << (y & 7))) !== 0;
      const pixel = (y * 128 + x) * 4;
      image.data[pixel] = on ? 159 : 3;
      image.data[pixel + 1] = on ? 255 : 19;
      image.data[pixel + 2] = on ? 207 : 15;
      image.data[pixel + 3] = 255;
    }
  }
  context.putImageData(image, 0, 0);
}

function render(snapshot) {
  if (snapshot.schema !== "catamaze.snapshot.v2") {
    throw new Error("unsupported snapshot schema");
  }
  paint(elements.map, snapshot.left_frame_hex);
  paint(elements.hud, snapshot.right_frame_hex);
  const gameSuffix = snapshot.mode === "PLAYING" || snapshot.mode === "RESULT"
    ? ` / ${snapshot.status}` : "";
  elements.status.textContent = `${snapshot.mode}${gameSuffix}`;
  elements.tick.textContent = String(snapshot.tick).padStart(5, "0");
  elements.hash.textContent = snapshot.state_hash;
  state.lastSnapshot = snapshot;
}

async function poll() {
  if (state.polling) return;
  state.polling = true;
  try {
    const snapshot = await api("/api/v1/snapshot");
    playObservableEvents(snapshot);
    render(snapshot);
    setConnection("online", "Native online");
  } catch (error) {
    console.error(error);
    setConnection("offline", "Connection lost");
  } finally {
    state.polling = false;
  }
}

async function sendInput(input) {
  ensureAudio();
  try {
    await api("/api/v1/input", {
      method: "POST",
      body: JSON.stringify({ input }),
    });
    window.setTimeout(poll, 20);
  } catch (error) {
    console.error(error);
    setConnection("offline", "Command rejected");
  }
}

function directionInput(direction) {
  const playing = state.lastSnapshot?.mode === "PLAYING";
  return playing && state.fireHeld ? `SHOOT_${direction}` : direction;
}

function setFire(held) {
  if (held) ensureAudio();
  state.fireHeld = held;
  elements.fire.classList.toggle("active", held);
}

function releaseFire(commit) {
  const wasHeld = state.fireHeld;
  setFire(false);
  if (commit && wasHeld) sendInput("FIRE");
}

function beginClear() {
  if (state.clearPressed) return;
  ensureAudio();
  state.clearPressed = true;
  state.clearLongCommitted = false;
  elements.clear.classList.add("active");
  state.clearTimer = window.setTimeout(() => {
    if (!state.clearPressed || state.clearLongCommitted) return;
    state.clearLongCommitted = true;
    sendInput("CLEAR_LONG");
  }, 800);
}

function releaseClear(commitShort) {
  if (!state.clearPressed) return;
  window.clearTimeout(state.clearTimer);
  const wasLong = state.clearLongCommitted;
  state.clearPressed = false;
  state.clearLongCommitted = false;
  state.clearTimer = null;
  elements.clear.classList.remove("active");
  if (commitShort && !wasLong) sendInput("CLEAR_SHORT");
}

document.querySelectorAll("[data-direction]").forEach((button) => {
  button.addEventListener("click", () => sendInput(directionInput(button.dataset.direction)));
});

elements.fire.addEventListener("pointerdown", (event) => {
  event.preventDefault();
  elements.fire.setPointerCapture(event.pointerId);
  setFire(true);
});
elements.fire.addEventListener("pointerup", () => releaseFire(true));
elements.fire.addEventListener("pointercancel", () => releaseFire(false));
elements.fire.addEventListener("lostpointercapture", () => releaseFire(false));

elements.clear.addEventListener("pointerdown", (event) => {
  event.preventDefault();
  elements.clear.setPointerCapture(event.pointerId);
  beginClear();
});
elements.clear.addEventListener("pointerup", () => releaseClear(true));
elements.clear.addEventListener("pointercancel", () => releaseClear(false));
elements.clear.addEventListener("lostpointercapture", () => releaseClear(false));

elements.pause.addEventListener("click", () => api("/api/v1/clock", {
  method: "POST", body: JSON.stringify({ mode: "PAUSED" }),
}).catch(console.error));
elements.realtime.addEventListener("click", () => api("/api/v1/clock", {
  method: "POST", body: JSON.stringify({ mode: "REALTIME" }),
}).catch(console.error));
elements.step.addEventListener("click", () => api("/api/v1/clock", {
  method: "POST", body: JSON.stringify({ command: "STEP" }),
}).then(() => window.setTimeout(poll, 20)).catch(console.error));

elements.resetForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  try {
    await api("/api/v1/reset", {
      method: "POST",
      body: JSON.stringify({ seed: elements.seed.value.trim() }),
    });
    window.setTimeout(poll, 20);
  } catch (error) {
    console.error(error);
    setConnection("offline", "Reset rejected");
  }
});

const keyDirections = new Map([
  ["ArrowUp", "UP"],
  ["ArrowDown", "DOWN"],
  ["ArrowLeft", "LEFT"],
  ["ArrowRight", "RIGHT"],
]);

window.addEventListener("keydown", (event) => {
  if (event.target instanceof HTMLInputElement) return;
  ensureAudio();
  if (event.code === "Space") {
    event.preventDefault();
    if (!event.repeat) setFire(true);
    return;
  }
  if (event.repeat) return;
  const direction = keyDirections.get(event.key);
  if (direction) {
    event.preventDefault();
    sendInput(directionInput(direction));
  } else if (event.key.toLowerCase() === "c") {
    beginClear();
  } else if (event.key.toLowerCase() === "p") {
    elements.pause.click();
  } else if (event.key.toLowerCase() === "t") {
    elements.step.click();
  }
});

window.addEventListener("keyup", (event) => {
  if (event.code === "Space") releaseFire(true);
  if (event.key.toLowerCase() === "c") releaseClear(true);
});
window.addEventListener("blur", () => {
  releaseFire(false);
  releaseClear(false);
});

poll();
window.setInterval(poll, 150);
