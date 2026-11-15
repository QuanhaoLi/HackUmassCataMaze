// Created at: 2026-11-15 06:48 EST
// Created by: Codex
// Last Modified at: 2026-11-15 06:48 EST
// Last Modified by: Codex
// Drives the static showcase in real Chrome, validates interactions/layout, and captures screenshots.

import fs from "node:fs";

const [debugPortText, url, widthText, heightText, outputPath] = process.argv.slice(2);
const debugPort = Number.parseInt(debugPortText, 10);
const width = Number.parseInt(widthText, 10);
const height = Number.parseInt(heightText, 10);

if (!debugPort || !url || !width || !height || !outputPath) {
  throw new Error("usage: capture_showcase.mjs <debug-port> <url> <width> <height> <output>");
}

const pages = await fetch(`http://127.0.0.1:${debugPort}/json/list`).then((response) => response.json());
const page = pages.find((candidate) => candidate.type === "page");
if (!page) throw new Error("Chrome DevTools exposed no page target");

const socket = new WebSocket(page.webSocketDebuggerUrl);
const pending = new Map();
const browserErrors = [];
let nextId = 1;

await new Promise((resolve, reject) => {
  socket.addEventListener("open", resolve, { once: true });
  socket.addEventListener("error", reject, { once: true });
});

socket.addEventListener("message", (event) => {
  const message = JSON.parse(event.data);
  if (message.method === "Runtime.exceptionThrown") {
    browserErrors.push(message.params.exceptionDetails.exception?.description || message.params.exceptionDetails.text);
  }
  if (message.method === "Runtime.consoleAPICalled" && message.params.type === "error") {
    browserErrors.push(message.params.args.map((argument) => argument.value || argument.description).join(" "));
  }
  if (!message.id || !pending.has(message.id)) return;
  const { resolve, reject } = pending.get(message.id);
  pending.delete(message.id);
  if (message.error) reject(new Error(message.error.message));
  else resolve(message.result);
});

function rpc(method, params = {}) {
  const id = nextId;
  nextId += 1;
  return new Promise((resolve, reject) => {
    pending.set(id, { resolve, reject });
    socket.send(JSON.stringify({ id, method, params }));
  });
}

async function evaluate(expression, awaitPromise = false) {
  const result = await rpc("Runtime.evaluate", { expression, awaitPromise, returnByValue: true });
  if (result.exceptionDetails) throw new Error(result.exceptionDetails.text);
  return result.result.value;
}

async function capture(path) {
  const screenshot = await rpc("Page.captureScreenshot", {
    format: "png",
    fromSurface: true,
    captureBeyondViewport: true,
  });
  fs.writeFileSync(path, Buffer.from(screenshot.data, "base64"));
}

await rpc("Page.enable");
await rpc("Runtime.enable");
await rpc("Emulation.setDeviceMetricsOverride", {
  width,
  height,
  screenWidth: width,
  screenHeight: height,
  deviceScaleFactor: 1,
  mobile: width < 600,
});
await rpc("Page.navigate", { url });

for (let attempt = 0; attempt < 120; attempt += 1) {
  if (await evaluate("document.readyState") === "complete") break;
  await new Promise((resolve) => setTimeout(resolve, 25));
}
await new Promise((resolve) => setTimeout(resolve, 350));

const initial = await evaluate("window.__CATAMAZE_SHOWCASE__.snapshot()");
if (initial.mode !== "IDLE" || initial.runtime !== "BROWSER_SIM" || !initial.eyeFrame) {
  throw new Error(`showcase did not boot into Companion Idle: ${JSON.stringify(initial)}`);
}

await capture(outputPath);

const interaction = await evaluate(`(async () => {
  const key = (type, code, value) => window.dispatchEvent(new KeyboardEvent(type, {
    code, key: value, bubbles: true
  }));
  const sleep = (milliseconds) => new Promise((resolve) => setTimeout(resolve, milliseconds));
  document.querySelector('#sound-toggle').click();

  key('keydown', 'Space', ' ');
  key('keyup', 'Space', ' ');
  await sleep(30);
  const wake = window.__CATAMAZE_SHOWCASE__.snapshot();

  key('keydown', 'Space', ' ');
  key('keyup', 'Space', ' ');
  await sleep(30);
  const started = window.__CATAMAZE_SHOWCASE__.snapshot();

  key('keydown', 'ArrowRight', 'ArrowRight');
  await sleep(20);
  const queued = window.__CATAMAZE_SHOWCASE__.snapshot();
  key('keydown', 'KeyC', 'c');
  key('keyup', 'KeyC', 'c');
  await sleep(20);
  const cleared = window.__CATAMAZE_SHOWCASE__.snapshot();

  key('keydown', 'Space', ' ');
  key('keydown', 'ArrowRight', 'ArrowRight');
  key('keyup', 'Space', ' ');
  await sleep(20);
  const sampled = window.__CATAMAZE_SHOWCASE__.snapshot();
  const stepped = window.__CATAMAZE_SHOWCASE__.step();

  key('keydown', 'ArrowDown', 'ArrowDown');
  key('keydown', 'ArrowLeft', 'ArrowLeft');
  key('keydown', 'ArrowUp', 'ArrowUp');
  const beforePause = window.__CATAMAZE_SHOWCASE__.snapshot();
  key('keydown', 'KeyC', 'c');
  await sleep(850);
  key('keyup', 'KeyC', 'c');
  await sleep(30);
  const paused = window.__CATAMAZE_SHOWCASE__.snapshot();

  key('keydown', 'KeyC', 'c');
  key('keyup', 'KeyC', 'c');
  await sleep(20);
  const resumed = window.__CATAMAZE_SHOWCASE__.snapshot();
  const prompted = window.__CATAMAZE_SHOWCASE__.forceInactivity();
  key('keydown', 'KeyC', 'c');
  key('keyup', 'KeyC', 'c');
  await sleep(20);
  const continued = window.__CATAMAZE_SHOWCASE__.snapshot();

  return {wake, started, queued, cleared, sampled, stepped, beforePause, paused, resumed, prompted, continued};
})()`, true);

if (interaction.wake.mode !== "HOME") {
  throw new Error(`Wake input was not consumed into Home: ${JSON.stringify(interaction.wake)}`);
}
if (interaction.started.mode !== "PLAYING" || interaction.started.tick !== 0) {
  throw new Error(`second FIRE did not start a fresh run: ${JSON.stringify(interaction.started)}`);
}
if (interaction.queued.queue.length !== 1 || interaction.cleared.queue.length !== 0) {
  throw new Error(`direction/CLEAR short queue contract failed: ${JSON.stringify(interaction)}`);
}
if (interaction.sampled.queue[0] !== "SHOOT_RIGHT" || interaction.stepped.player.ammo !== 2) {
  throw new Error(`FIRE sampling or wall-safe ammo spending failed: ${JSON.stringify(interaction)}`);
}
if (interaction.paused.mode !== "PAUSED" || interaction.paused.queue.length === 0) {
  throw new Error(`CLEAR long did not pause without clearing remaining actions: ${JSON.stringify(interaction.paused)}`);
}
if (interaction.resumed.mode !== "PLAYING" || interaction.prompted.mode !== "INACTIVITY_PROMPT" ||
    interaction.continued.mode !== "PLAYING") {
  throw new Error(`pause/inactivity continuation flow failed: ${JSON.stringify(interaction)}`);
}

const layout = JSON.parse(await evaluate(`JSON.stringify({
  release: document.body.dataset.release,
  clientWidth: document.documentElement.clientWidth,
  scrollWidth: document.documentElement.scrollWidth,
  bodyScrollWidth: document.body.scrollWidth,
  mapWidth: document.querySelector('#map-screen').getBoundingClientRect().width,
  hudWidth: document.querySelector('#hud-screen').getBoundingClientRect().width,
  controlSizes: [...document.querySelectorAll('.key, .round-key')].map((element) => {
    const rect = element.getBoundingClientRect();
    return [rect.width, rect.height];
  }),
  litPixels: [...document.querySelector('#map-screen').getContext('2d').getImageData(0, 0, 128, 64).data]
    .filter((value, index) => index % 4 !== 3 && value > 40).length
})`));

if (layout.release !== "2026.11.15.1" || layout.scrollWidth > layout.clientWidth ||
    layout.bodyScrollWidth > layout.clientWidth || !layout.mapWidth || !layout.hudWidth) {
  throw new Error(`showcase layout contract failed at ${width}px: ${JSON.stringify(layout)}`);
}
if (layout.controlSizes.some(([controlWidth, controlHeight]) => controlWidth < 44 || controlHeight < 44)) {
  throw new Error(`touch target below 44px at ${width}px: ${JSON.stringify(layout.controlSizes)}`);
}
if (layout.litPixels === 0) throw new Error("left OLED rendered no lit pixels");
if (browserErrors.length > 0) throw new Error(`browser emitted errors: ${browserErrors.join(" | ")}`);

const playingPath = outputPath.replace(/\.png$/, "-playing.png");
await capture(playingPath);
await evaluate("window.__CATAMAZE_SHOWCASE__.reset()");
await new Promise((resolve) => setTimeout(resolve, 80));

console.log(`SHOWCASE_CAPTURE_OK width=${width} height=${height} layout=${JSON.stringify({
  clientWidth: layout.clientWidth,
  mapWidth: layout.mapWidth,
  hudWidth: layout.hudWidth,
  minimumControl: Math.min(...layout.controlSizes.flat()),
  playingPath,
})}`);
socket.close();
