/*
Created at: 2026-11-14 02:37 EST
Created by: Codex
Last Modified at: 2026-11-14 02:37 EST
Last Modified by: Codex
Resolves physical button semantics, calls the versioned API, and paints authoritative framebuffers.
*/

"use strict";

const state = {
  fireHeld: false,
  polling: false,
  lastSnapshot: null,
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
  wait: document.querySelector("#wait"),
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
  if (snapshot.schema !== "catamaze.snapshot.v1") {
    throw new Error("unsupported snapshot schema");
  }
  paint(elements.map, snapshot.map_frame_hex);
  paint(elements.hud, snapshot.hud_frame_hex);
  elements.status.textContent = snapshot.status;
  elements.tick.textContent = String(snapshot.tick).padStart(5, "0");
  elements.hash.textContent = snapshot.state_hash;
  state.lastSnapshot = snapshot;
}

async function poll() {
  if (state.polling) return;
  state.polling = true;
  try {
    const snapshot = await api("/api/v1/snapshot");
    render(snapshot);
    setConnection("online", "Native online");
  } catch (error) {
    console.error(error);
    setConnection("offline", "Connection lost");
  } finally {
    state.polling = false;
  }
}

async function sendAction(action) {
  try {
    await api("/api/v1/action", {
      method: "POST",
      body: JSON.stringify({ action }),
    });
    window.setTimeout(poll, 20);
  } catch (error) {
    console.error(error);
    setConnection("offline", "Command rejected");
  }
}

function directionAction(direction) {
  return `${state.fireHeld ? "SHOOT" : "MOVE"}_${direction}`;
}

function setFire(held) {
  state.fireHeld = held;
  elements.fire.classList.toggle("active", held);
}

document.querySelectorAll("[data-direction]").forEach((button) => {
  button.addEventListener("click", () => sendAction(directionAction(button.dataset.direction)));
});

elements.fire.addEventListener("pointerdown", (event) => {
  event.preventDefault();
  elements.fire.setPointerCapture(event.pointerId);
  setFire(true);
});
elements.fire.addEventListener("pointerup", () => setFire(false));
elements.fire.addEventListener("pointercancel", () => setFire(false));
elements.fire.addEventListener("lostpointercapture", () => setFire(false));
elements.wait.addEventListener("click", () => sendAction("WAIT"));
elements.clear.addEventListener("click", () => sendAction("CLEAR"));

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
  if (event.code === "Space") {
    event.preventDefault();
    setFire(true);
    return;
  }
  if (event.repeat || event.target instanceof HTMLInputElement) return;
  const direction = keyDirections.get(event.key);
  if (direction) {
    event.preventDefault();
    sendAction(directionAction(direction));
  } else if (event.key.toLowerCase() === "w") {
    sendAction("WAIT");
  } else if (event.key.toLowerCase() === "c") {
    sendAction("CLEAR");
  } else if (event.key.toLowerCase() === "p") {
    elements.pause.click();
  } else if (event.key.toLowerCase() === "t") {
    elements.step.click();
  }
});

window.addEventListener("keyup", (event) => {
  if (event.code === "Space") setFire(false);
});
window.addEventListener("blur", () => setFire(false));

poll();
window.setInterval(poll, 150);
