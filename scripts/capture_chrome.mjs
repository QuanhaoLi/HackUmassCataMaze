// Created at: 2026-11-14 02:48 EST
// Created by: Codex
// Last Modified at: 2026-11-14 11:41 EST
// Last Modified by: Codex
// Captures one exact CSS viewport through Chrome DevTools and rejects horizontal overflow.

import fs from "node:fs";

const [debugPortText, url, widthText, heightText, outputPath] = process.argv.slice(2);
const debugPort = Number.parseInt(debugPortText, 10);
const width = Number.parseInt(widthText, 10);
const height = Number.parseInt(heightText, 10);

if (!debugPort || !url || !width || !height || !outputPath) {
  throw new Error("usage: capture_chrome.mjs <debug-port> <url> <width> <height> <output>");
}

const pages = await fetch(`http://127.0.0.1:${debugPort}/json/list`).then((response) => response.json());
const page = pages.find((candidate) => candidate.type === "page");
if (!page) throw new Error("Chrome DevTools exposed no page target");

const socket = new WebSocket(page.webSocketDebuggerUrl);
const pending = new Map();
const browserErrors = [];
let nextId = 1;

const opened = new Promise((resolve, reject) => {
  socket.addEventListener("open", resolve, { once: true });
  socket.addEventListener("error", reject, { once: true });
});

socket.addEventListener("message", (event) => {
  const message = JSON.parse(event.data);
  if (message.method === "Runtime.exceptionThrown") {
    browserErrors.push(message.params.exceptionDetails.text);
  }
  if (message.method === "Runtime.consoleAPICalled" && message.params.type === "error") {
    browserErrors.push("console.error");
  }
  if (!message.id || !pending.has(message.id)) return;
  const { resolve, reject } = pending.get(message.id);
  pending.delete(message.id);
  if (message.error) reject(new Error(message.error.message));
  else resolve(message.result);
});

await opened;

function rpc(method, params = {}) {
  const id = nextId;
  nextId += 1;
  return new Promise((resolve, reject) => {
    pending.set(id, { resolve, reject });
    socket.send(JSON.stringify({ id, method, params }));
  });
}

await rpc("Page.enable");
await rpc("Runtime.enable");
await rpc("Emulation.setDeviceMetricsOverride", {
  width,
  height,
  deviceScaleFactor: 1,
  mobile: false,
});
await rpc("Page.navigate", { url });

for (let attempt = 0; attempt < 100; attempt += 1) {
  const result = await rpc("Runtime.evaluate", {
    expression: "document.readyState",
    returnByValue: true,
  });
  if (result.result.value === "complete") break;
  await new Promise((resolve) => setTimeout(resolve, 25));
}
await new Promise((resolve) => setTimeout(resolve, 700));

const interactionResult = await rpc("Runtime.evaluate", {
  expression: `(async () => {
    const key = (type, code, value) => window.dispatchEvent(
      new KeyboardEvent(type, {code, key: value}));
    const sleep = (milliseconds) => new Promise((resolve) => setTimeout(resolve, milliseconds));
    key("keydown", "Space", " ");
    key("keyup", "Space", " ");
    await sleep(100);
    key("keydown", "Space", " ");
    key("keyup", "Space", " ");
    await sleep(100);
    key("keydown", "ArrowRight", "ArrowRight");
    await sleep(80);
    key("keydown", "KeyC", "c");
    await sleep(850);
    key("keyup", "KeyC", "c");
    await sleep(100);
    return fetch('/api/v1/snapshot').then((response) => response.json());
  })()`,
  awaitPromise: true,
  returnByValue: true,
});
const paused = interactionResult.result.value;
if (paused.mode !== "ACTIVE" || paused.system_mode !== "PAUSED" ||
    paused.tick !== 0 || paused.player.queue !== 1) {
  throw new Error(`CLEAR long did not pause and preserve queue: ${JSON.stringify(paused)}`);
}

const resumedResult = await rpc("Runtime.evaluate", {
  expression: `(async () => {
    const key = (type, code, value) => window.dispatchEvent(
      new KeyboardEvent(type, {code, key: value}));
    const sleep = (milliseconds) => new Promise((resolve) => setTimeout(resolve, milliseconds));
    key("keydown", "KeyC", "c");
    key("keyup", "KeyC", "c");
    await sleep(100);
    document.querySelector("#step").click();
    await sleep(100);
    return fetch('/api/v1/snapshot').then((response) => response.json());
  })()`,
  awaitPromise: true,
  returnByValue: true,
});
const resumed = resumedResult.result.value;
if (resumed.mode !== "ACTIVE" || resumed.system_mode !== "PLAYING" ||
    resumed.tick !== 1 || resumed.player.queue !== 0) {
  throw new Error(`CLEAR short did not resume preserved queue: ${JSON.stringify(resumed)}`);
}

const shootingResult = await rpc("Runtime.evaluate", {
  expression: `(async () => {
    const key = (type, code, value) => window.dispatchEvent(
      new KeyboardEvent(type, {code, key: value}));
    const sleep = (milliseconds) => new Promise((resolve) => setTimeout(resolve, milliseconds));
    key("keydown", "Space", " ");
    key("keydown", "ArrowRight", "ArrowRight");
    key("keyup", "Space", " ");
    await sleep(100);
    document.querySelector("#step").click();
    await sleep(100);
    return fetch('/api/v1/snapshot').then((response) => response.json());
  })()`,
  awaitPromise: true,
  returnByValue: true,
});
const shooting = shootingResult.result.value;
if (shooting.tick !== 2 || !shooting.last_events.some((event) => event.type === "PLAYER_SHOT")) {
  throw new Error(`FIRE sampling did not enqueue one shot: ${JSON.stringify(shooting)}`);
}

const inactivityResult = await rpc("Runtime.evaluate", {
  expression: `(async () => {
    await fetch('/api/v1/clock', {
      method: 'POST', headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({command: 'ELAPSE_INACTIVITY'})
    });
    await new Promise((resolve) => setTimeout(resolve, 100));
    return fetch('/api/v1/snapshot').then((response) => response.json());
  })()`,
  awaitPromise: true,
  returnByValue: true,
});
const inactive = inactivityResult.result.value;
if (inactive.mode !== "INACTIVITY_PROMPT" || inactive.system_mode !== "PAUSED" ||
    inactive.tick !== shooting.tick || inactive.state_hash !== shooting.state_hash ||
    inactive.system.prompt_focus !== 0) {
  throw new Error(`inactivity did not freeze into default-continue prompt: ${JSON.stringify(inactive)}`);
}

const sleepResult = await rpc("Runtime.evaluate", {
  expression: `(async () => {
    const key = (type, code, value) => window.dispatchEvent(
      new KeyboardEvent(type, {code, key: value}));
    const sleep = (milliseconds) => new Promise((resolve) => setTimeout(resolve, milliseconds));
    key("keydown", "KeyC", "c");
    key("keyup", "KeyC", "c");
    await sleep(100);
    const continued = await fetch('/api/v1/snapshot').then((response) => response.json());
    if (continued.mode !== "ACTIVE" || continued.system_mode !== "PLAYING") return continued;
    await fetch('/api/v1/clock', {
      method: 'POST', headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({command: 'ELAPSE_INACTIVITY'})
    });
    await sleep(100);
    key("keydown", "ArrowDown", "ArrowDown");
    await sleep(50);
    key("keydown", "Space", " ");
    key("keyup", "Space", " ");
    await sleep(100);
    return fetch('/api/v1/snapshot').then((response) => response.json());
  })()`,
  awaitPromise: true,
  returnByValue: true,
});
if (sleepResult.result.value.mode !== "IDLE" ||
    sleepResult.result.value.system.has_active_session !== false) {
  throw new Error(`explicit prompt Sleep did not return to companion: ${JSON.stringify(sleepResult.result.value)}`);
}

await rpc("Runtime.evaluate", {
  expression: `(() => {
    document.querySelector("#seed").value = "0x000000000134fd5a";
    document.querySelector("#reset-form").dispatchEvent(new Event("submit", {bubbles: true, cancelable: true}));
    return true;
  })()`,
  returnByValue: true,
});
await new Promise((resolve) => setTimeout(resolve, 250));
const resetResult = await rpc("Runtime.evaluate", {
  expression: "fetch('/api/v1/snapshot').then((response) => response.json())",
  awaitPromise: true,
  returnByValue: true,
});
if (resetResult.result.value.mode !== "IDLE" || resetResult.result.value.system_mode !== "HOME" ||
    resetResult.result.value.tick !== 0 ||
    resetResult.result.value.player.queue !== 0) {
  throw new Error(`browser reset did not restore initial state: ${JSON.stringify(resetResult.result.value)}`);
}

const inputIsolationResult = await rpc("Runtime.evaluate", {
  expression: `(async () => {
    const seed = document.querySelector("#seed");
    seed.focus();
    seed.dispatchEvent(new KeyboardEvent("keydown", {code: "Space", key: " ", bubbles: true}));
    seed.dispatchEvent(new KeyboardEvent("keyup", {code: "Space", key: " ", bubbles: true}));
    await new Promise((resolve) => setTimeout(resolve, 100));
    seed.blur();
    return fetch('/api/v1/snapshot').then((response) => response.json());
  })()`,
  awaitPromise: true,
  returnByValue: true,
});
if (inputIsolationResult.result.value.mode !== "IDLE") {
  throw new Error(`typing in seed input leaked into game controls: ${JSON.stringify(inputIsolationResult.result.value)}`);
}

if (width >= 1000) {
  const reviewed = [
    ["LOOK_RIGHT", "look-right"],
    ["CURIOUS", "curious"],
    ["SURPRISED", "surprised"],
    ["NEUTRAL", "neutral-return"],
  ];
  for (const [expected, suffix] of reviewed) {
    const expressionResult = await rpc("Runtime.evaluate", {
      expression: `(async () => {
        await fetch('/api/v1/clock', {
          method: 'POST', headers: {'Content-Type': 'application/json'},
          body: JSON.stringify({command: 'ELAPSE_INACTIVITY'})
        });
        await new Promise((resolve) => setTimeout(resolve, 100));
        return fetch('/api/v1/snapshot').then((response) => response.json());
      })()`,
      awaitPromise: true,
      returnByValue: true,
    });
    if (expressionResult.result.value.mode !== "IDLE" ||
        expressionResult.result.value.companion_frame !== expected) {
      throw new Error(`companion expression did not reach ${expected}: ${JSON.stringify(expressionResult.result.value)}`);
    }
    await new Promise((resolve) => setTimeout(resolve, 250));
    const expressionShot = await rpc("Page.captureScreenshot", {
      format: "png", fromSurface: true, captureBeyondViewport: false,
    });
    const expressionPath = outputPath.replace(/\.png$/, `-${suffix}.png`);
    fs.writeFileSync(expressionPath, Buffer.from(expressionShot.data, "base64"));
  }
}

const layoutResult = await rpc("Runtime.evaluate", {
  expression: `JSON.stringify({
    clientWidth: document.documentElement.clientWidth,
    scrollWidth: document.documentElement.scrollWidth,
    bodyScrollWidth: document.body.scrollWidth,
    connection: document.querySelector("#connection-label")?.textContent,
    mapWidth: document.querySelector("#map-screen")?.getBoundingClientRect().width,
    hudWidth: document.querySelector("#hud-screen")?.getBoundingClientRect().width
  })`,
  returnByValue: true,
});
const layout = JSON.parse(layoutResult.result.value);
if (layout.scrollWidth > layout.clientWidth || layout.bodyScrollWidth > layout.clientWidth) {
  throw new Error(`horizontal overflow at ${width}px: ${JSON.stringify(layout)}`);
}
if (layout.connection !== "Native online" || !layout.mapWidth || !layout.hudWidth) {
  throw new Error(`page did not become ready: ${JSON.stringify(layout)}`);
}
if (browserErrors.length > 0) {
  throw new Error(`browser emitted errors: ${browserErrors.join(", ")}`);
}

const screenshot = await rpc("Page.captureScreenshot", {
  format: "png",
  fromSurface: true,
  captureBeyondViewport: false,
});
fs.writeFileSync(outputPath, Buffer.from(screenshot.data, "base64"));
console.log(`CAPTURE_OK width=${width} height=${height} layout=${JSON.stringify(layout)}`);
socket.close();
