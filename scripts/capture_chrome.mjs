// Created at: 2026-11-14 02:48 EST
// Created by: Codex
// Last Modified at: 2026-11-14 02:48 EST
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

await rpc("Runtime.evaluate", {
  expression: `(() => {
    window.dispatchEvent(new KeyboardEvent("keydown", {code: "Space", key: " "}));
    window.dispatchEvent(new KeyboardEvent("keydown", {code: "ArrowRight", key: "ArrowRight"}));
    window.dispatchEvent(new KeyboardEvent("keyup", {code: "Space", key: " "}));
    window.dispatchEvent(new KeyboardEvent("keydown", {code: "KeyW", key: "w"}));
    window.dispatchEvent(new KeyboardEvent("keydown", {code: "KeyC", key: "c"}));
    document.querySelector("#pause").click();
    document.querySelector("#step").click();
    return true;
  })()`,
  returnByValue: true,
});
await new Promise((resolve) => setTimeout(resolve, 250));
const interactionResult = await rpc("Runtime.evaluate", {
  expression: "fetch('/api/v1/snapshot').then((response) => response.json())",
  awaitPromise: true,
  returnByValue: true,
});
if (interactionResult.result.value.tick !== 1) {
  throw new Error(`browser control sequence did not step exactly once: ${JSON.stringify(interactionResult.result.value)}`);
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
if (resetResult.result.value.tick !== 0 || resetResult.result.value.player.queue !== 0) {
  throw new Error(`browser reset did not restore initial state: ${JSON.stringify(resetResult.result.value)}`);
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
