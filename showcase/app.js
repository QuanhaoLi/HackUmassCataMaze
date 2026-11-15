/*
Created at: 2026-11-15 06:41 EST
Created by: Codex
Last Modified at: 2026-11-15 06:41 EST
Last Modified by: Codex
Runs the backend-free CataMaze showcase, deterministic demo maze, OLEDs, and six-button gestures.
*/

"use strict";

const RELEASE = "2026.11.15.1";
const TICK_MS = 600;
const INACTIVITY_MS = 30000;
const CLEAR_LONG_MS = 800;
const QUEUE_CAPACITY = 32;
const MAP_PRESETS = [12, 20, 30, 50];
const DIRECTIONS = [
  { name: "UP", dx: 0, dy: -1 },
  { name: "RIGHT", dx: 1, dy: 0 },
  { name: "DOWN", dx: 0, dy: 1 },
  { name: "LEFT", dx: -1, dy: 0 },
];

const MODE = Object.freeze({
  IDLE: "IDLE",
  HOME: "HOME",
  SETUP: "SETUP",
  SYSTEM: "SYSTEM",
  ABOUT: "ABOUT",
  PLAYING: "PLAYING",
  PAUSED: "PAUSED",
  CONFIRM_HOME: "CONFIRM_HOME",
  PROMPT: "INACTIVITY_PROMPT",
  RESULT: "RESULT",
});

const OLED_OFF = "#03130f";
const OLED_ON = "#a7ffd2";

// Column-major five-by-seven product glyphs match the portable renderer's visual language.
const FONT = Object.freeze({
  "0": [0x3e, 0x51, 0x49, 0x45, 0x3e], "1": [0x00, 0x42, 0x7f, 0x40, 0x00],
  "2": [0x42, 0x61, 0x51, 0x49, 0x46], "3": [0x21, 0x41, 0x45, 0x4b, 0x31],
  "4": [0x18, 0x14, 0x12, 0x7f, 0x10], "5": [0x27, 0x45, 0x45, 0x45, 0x39],
  "6": [0x3c, 0x4a, 0x49, 0x49, 0x30], "7": [0x01, 0x71, 0x09, 0x05, 0x03],
  "8": [0x36, 0x49, 0x49, 0x49, 0x36], "9": [0x06, 0x49, 0x49, 0x29, 0x1e],
  A: [0x7e, 0x11, 0x11, 0x11, 0x7e], B: [0x7f, 0x49, 0x49, 0x49, 0x36],
  C: [0x3e, 0x41, 0x41, 0x41, 0x22], D: [0x7f, 0x41, 0x41, 0x22, 0x1c],
  E: [0x7f, 0x49, 0x49, 0x49, 0x41], F: [0x7f, 0x09, 0x09, 0x09, 0x01],
  G: [0x3e, 0x41, 0x49, 0x49, 0x7a], H: [0x7f, 0x08, 0x08, 0x08, 0x7f],
  I: [0x00, 0x41, 0x7f, 0x41, 0x00], J: [0x20, 0x40, 0x41, 0x3f, 0x01],
  K: [0x7f, 0x08, 0x14, 0x22, 0x41], L: [0x7f, 0x40, 0x40, 0x40, 0x40],
  M: [0x7f, 0x02, 0x0c, 0x02, 0x7f], N: [0x7f, 0x04, 0x08, 0x10, 0x7f],
  O: [0x3e, 0x41, 0x41, 0x41, 0x3e], P: [0x7f, 0x09, 0x09, 0x09, 0x06],
  Q: [0x3e, 0x41, 0x51, 0x21, 0x5e], R: [0x7f, 0x09, 0x19, 0x29, 0x46],
  S: [0x46, 0x49, 0x49, 0x49, 0x31], T: [0x01, 0x01, 0x7f, 0x01, 0x01],
  U: [0x3f, 0x40, 0x40, 0x40, 0x3f], V: [0x1f, 0x20, 0x40, 0x20, 0x1f],
  W: [0x3f, 0x40, 0x38, 0x40, 0x3f], X: [0x63, 0x14, 0x08, 0x14, 0x63],
  Y: [0x07, 0x08, 0x70, 0x08, 0x07], Z: [0x61, 0x51, 0x49, 0x45, 0x43],
  "/": [0x20, 0x10, 0x08, 0x04, 0x02], ",": [0x00, 0x50, 0x30, 0x00, 0x00],
  "-": [0x08, 0x08, 0x08, 0x08, 0x08], ":": [0x00, 0x36, 0x36, 0x00, 0x00],
  ".": [0x00, 0x60, 0x60, 0x00, 0x00], ">": [0x00, 0x41, 0x22, 0x14, 0x08],
  "<": [0x08, 0x14, 0x22, 0x41, 0x00], " ": [0, 0, 0, 0, 0],
  "?": [0x02, 0x01, 0x51, 0x09, 0x06],
});

const HEART_FILLED = [0x36, 0x7f, 0x7f, 0x7f, 0x3e, 0x1c, 0x08];
const HEART_OUTLINE = [0x36, 0x49, 0x41, 0x41, 0x22, 0x14, 0x08];
const AMMO_FILLED = [0x1c, 0x3e, 0x3e, 0x3e, 0x3e, 0x3e, 0x3e];
const AMMO_OUTLINE = [0x1c, 0x22, 0x22, 0x22, 0x22, 0x22, 0x3e];

const elements = {
  map: document.querySelector("#map-screen"),
  hud: document.querySelector("#hud-screen"),
  status: document.querySelector("#status"),
  tick: document.querySelector("#tick"),
  queue: document.querySelector("#queue"),
  fire: document.querySelector("#fire"),
  clear: document.querySelector("#clear"),
  sound: document.querySelector("#sound-toggle"),
};

const contexts = {
  map: elements.map.getContext("2d", { alpha: false }),
  hud: elements.hud.getContext("2d", { alpha: false }),
};
contexts.map.imageSmoothingEnabled = false;
contexts.hud.imageSmoothingEnabled = false;

const state = {
  mode: MODE.IDLE,
  previousMode: MODE.PLAYING,
  homeFocus: 0,
  setupFocus: 0,
  systemFocus: 0,
  pauseFocus: 0,
  promptFocus: 0,
  confirmFocus: 0,
  resultFocus: 0,
  mapSize: 30,
  pendingMapSize: 30,
  runCounter: 0,
  game: null,
  idleSince: performance.now(),
  lastActivity: performance.now(),
  nextTickAt: Number.POSITIVE_INFINITY,
  lastEyeFrame: "",
  audioEnabled: true,
  audioContext: null,
};

const inputState = {
  firePressed: false,
  fireWakeConsumed: false,
  clearPressed: false,
  clearLongCommitted: false,
  clearWakeConsumed: false,
  clearTimer: null,
};

function clearCanvas(context) {
  context.fillStyle = OLED_OFF;
  context.fillRect(0, 0, 128, 64);
}

function pixel(context, x, y, on = true) {
  context.fillStyle = on ? OLED_ON : OLED_OFF;
  context.fillRect(Math.round(x), Math.round(y), 1, 1);
}

function fillRect(context, x, y, width, height, on = true) {
  context.fillStyle = on ? OLED_ON : OLED_OFF;
  context.fillRect(Math.round(x), Math.round(y), Math.round(width), Math.round(height));
}

function drawRect(context, x, y, width, height, on = true) {
  fillRect(context, x, y, width, 1, on);
  fillRect(context, x, y + height - 1, width, 1, on);
  fillRect(context, x, y, 1, height, on);
  fillRect(context, x + width - 1, y, 1, height, on);
}

function drawLine(context, x0, y0, x1, y1, on = true) {
  let x = x0;
  let y = y0;
  const dx = Math.abs(x1 - x0);
  const sx = x0 < x1 ? 1 : -1;
  const dy = -Math.abs(y1 - y0);
  const sy = y0 < y1 ? 1 : -1;
  let error = dx + dy;
  while (true) {
    pixel(context, x, y, on);
    if (x === x1 && y === y1) break;
    const doubled = 2 * error;
    if (doubled >= dy) { error += dy; x += sx; }
    if (doubled <= dx) { error += dx; y += sy; }
  }
}

function drawChar(context, x, y, character, on = true) {
  const columns = FONT[character] || FONT["?"];
  for (let column = 0; column < 5; column += 1) {
    for (let row = 0; row < 7; row += 1) {
      if ((columns[column] & (1 << row)) !== 0) pixel(context, x + column, y + row, on);
    }
  }
}

function drawText(context, x, y, text, on = true) {
  let cursor = x;
  for (const character of String(text).toUpperCase()) {
    drawChar(context, cursor, y, character, on);
    cursor += 6;
  }
}

function drawIcon(context, x, y, rows) {
  rows.forEach((row, rowIndex) => {
    for (let column = 0; column < 7; column += 1) {
      if ((row & (1 << (6 - column))) !== 0) pixel(context, x + column, y + rowIndex);
    }
  });
}

function drawMenuRow(context, y, label, selected) {
  if (selected) {
    fillRect(context, 1, y - 1, 126, 9);
    drawText(context, 4, y, `>${label}`, false);
  } else {
    drawText(context, 4, y, ` ${label}`);
  }
}

function wrapIndex(value, count) {
  return ((value % count) + count) % count;
}

function pad(value, width) {
  return String(Math.max(0, Math.trunc(value))).padStart(width, "0");
}

function tickBudget(size) {
  return size * 40;
}

function createRng(seed) {
  let current = seed >>> 0;
  return {
    next() {
      current ^= current << 13;
      current ^= current >>> 17;
      current ^= current << 5;
      current >>>= 0;
      return current / 0x100000000;
    },
    value() { return current >>> 0; },
  };
}

function shuffle(items, rng) {
  for (let index = items.length - 1; index > 0; index -= 1) {
    const swap = Math.floor(rng.next() * (index + 1));
    [items[index], items[swap]] = [items[swap], items[index]];
  }
  return items;
}

function keyFor(x, y) {
  return `${x},${y}`;
}

function inBounds(map, x, y) {
  return y >= 0 && y < map.length && x >= 0 && x < map.length;
}

function isWalkable(map, x, y) {
  return inBounds(map, x, y) && map[y][x] !== "#";
}

function breadthFirst(map, startX, startY) {
  const distance = new Map([[keyFor(startX, startY), 0]]);
  const queue = [{ x: startX, y: startY }];
  for (let index = 0; index < queue.length; index += 1) {
    const current = queue[index];
    const nextDistance = distance.get(keyFor(current.x, current.y)) + 1;
    for (const direction of DIRECTIONS) {
      const x = current.x + direction.dx;
      const y = current.y + direction.dy;
      const key = keyFor(x, y);
      if (!isWalkable(map, x, y) || distance.has(key)) continue;
      distance.set(key, nextDistance);
      queue.push({ x, y });
    }
  }
  return { distance, cells: queue };
}

function generateMaze(size, seed) {
  const rng = createRng(seed);
  const map = Array.from({ length: size }, () => Array(size).fill("#"));
  const stack = [{ x: 1, y: 1 }];
  map[1][1] = "S";

  while (stack.length > 0) {
    const current = stack[stack.length - 1];
    const candidates = shuffle(DIRECTIONS.map((direction) => ({
      x: current.x + direction.dx * 2,
      y: current.y + direction.dy * 2,
      wallX: current.x + direction.dx,
      wallY: current.y + direction.dy,
    })), rng).filter((candidate) => (
      candidate.x >= 1 && candidate.y >= 1 &&
      candidate.x <= size - 3 && candidate.y <= size - 3 &&
      map[candidate.y][candidate.x] === "#"
    ));

    if (candidates.length === 0) {
      stack.pop();
      continue;
    }
    const next = candidates[0];
    map[next.wallY][next.wallX] = ".";
    map[next.y][next.x] = ".";
    stack.push({ x: next.x, y: next.y });
  }

  const traversal = breadthFirst(map, 1, 1);
  const ordered = traversal.cells
    .map((cell) => ({ ...cell, distance: traversal.distance.get(keyFor(cell.x, cell.y)) }))
    .sort((left, right) => right.distance - left.distance || left.y - right.y || left.x - right.x);
  const exit = ordered[0];
  map[exit.y][exit.x] = "E";
  return { map, ordered, exit, rngState: rng.value() };
}

function chooseSpawn(ordered, targetDistance, used) {
  const candidates = ordered.filter((cell) => !used.has(keyFor(cell.x, cell.y)) && cell.distance > 5);
  candidates.sort((left, right) => (
    Math.abs(left.distance - targetDistance) - Math.abs(right.distance - targetDistance) ||
    left.y - right.y || left.x - right.x
  ));
  const selected = candidates[0] || ordered[0];
  used.add(keyFor(selected.x, selected.y));
  return selected;
}

function newEntity(id, persona, position) {
  return {
    id,
    persona,
    x: position.x,
    y: position.y,
    hp: 5,
    ammo: 3,
    recharge: 0,
    alive: true,
    heading: id % DIRECTIONS.length,
    visits: new Map([[keyFor(position.x, position.y), 1]]),
  };
}

function startGame(reuseSeed = false) {
  state.mapSize = state.pendingMapSize;
  if (!reuseSeed) state.runCounter += 1;
  const seed = reuseSeed && state.game ? state.game.seed : (0x0134fd5a ^ state.runCounter) >>> 0;
  const generated = generateMaze(state.mapSize, seed);
  const maximumDistance = generated.ordered[0].distance;
  const used = new Set([keyFor(1, 1), keyFor(generated.exit.x, generated.exit.y)]);
  const aggressive = chooseSpawn(generated.ordered, Math.min(18, maximumDistance), used);
  const cautious = chooseSpawn(generated.ordered, Math.min(Math.max(32, state.mapSize * 2), maximumDistance), used);
  const explorer = chooseSpawn(generated.ordered, maximumDistance - 3, used);

  state.game = {
    seed,
    map: generated.map,
    exit: generated.exit,
    rng: createRng(generated.rngState ^ 0x9e3779b9),
    tick: 0,
    maxTicks: tickBudget(state.mapSize),
    queue: [],
    bullets: [],
    player: { x: 1, y: 1, hp: 5, ammo: 3, recharge: 0, alive: true },
    enemies: [
      newEntity(0, "AGGRESSIVE", aggressive),
      newEntity(1, "CAUTIOUS", cautious),
      newEntity(2, "EXPLORER", explorer),
    ],
    result: "",
    lastEvent: "",
  };
  state.mode = MODE.PLAYING;
  state.pauseFocus = 0;
  state.resultFocus = 0;
  state.nextTickAt = performance.now() + TICK_MS;
  noteActivity();
  render();
}

function occupiedByEnemy(game, x, y, exceptId = -1) {
  return game.enemies.some((enemy) => enemy.alive && enemy.id !== exceptId && enemy.x === x && enemy.y === y);
}

function canMovePlayer(game, x, y) {
  return isWalkable(game.map, x, y) && !occupiedByEnemy(game, x, y);
}

function canMoveEnemy(game, enemy, x, y) {
  return isWalkable(game.map, x, y) && !(game.player.x === x && game.player.y === y) &&
    !occupiedByEnemy(game, x, y, enemy.id);
}

function lineOfFire(game, fromX, fromY, toX, toY) {
  let direction = null;
  if (fromX === toX) direction = toY < fromY ? DIRECTIONS[0] : DIRECTIONS[2];
  if (fromY === toY) direction = toX > fromX ? DIRECTIONS[1] : DIRECTIONS[3];
  if (!direction) return null;
  let x = fromX + direction.dx;
  let y = fromY + direction.dy;
  let range = 1;
  while (inBounds(game.map, x, y) && game.map[y][x] !== "#") {
    if (x === toX && y === toY) return { direction, range };
    x += direction.dx;
    y += direction.dy;
    range += 1;
  }
  return null;
}

function pathStep(game, enemy, towardPlayer = true) {
  const start = { x: enemy.x, y: enemy.y };
  const queue = [start];
  const previous = new Map([[keyFor(start.x, start.y), null]]);
  let destination = null;
  for (let index = 0; index < queue.length; index += 1) {
    const current = queue[index];
    if (current.x === game.player.x && current.y === game.player.y) {
      destination = current;
      break;
    }
    for (const direction of DIRECTIONS) {
      const x = current.x + direction.dx;
      const y = current.y + direction.dy;
      const key = keyFor(x, y);
      if (!isWalkable(game.map, x, y) || previous.has(key)) continue;
      previous.set(key, current);
      queue.push({ x, y });
    }
  }
  if (!destination) return null;
  let current = destination;
  let prior = previous.get(keyFor(current.x, current.y));
  while (prior && !(prior.x === start.x && prior.y === start.y)) {
    current = prior;
    prior = previous.get(keyFor(current.x, current.y));
  }
  if (towardPlayer) return current;

  const legal = DIRECTIONS.map((direction) => ({
    x: enemy.x + direction.dx,
    y: enemy.y + direction.dy,
  })).filter((cell) => canMoveEnemy(game, enemy, cell.x, cell.y));
  legal.sort((left, right) => (
    Math.abs(right.x - game.player.x) + Math.abs(right.y - game.player.y) -
    (Math.abs(left.x - game.player.x) + Math.abs(left.y - game.player.y))
  ));
  return legal[0] || null;
}

function explorerStep(game, enemy) {
  const rotated = DIRECTIONS.map((_, index) => DIRECTIONS[(index + enemy.heading) % DIRECTIONS.length]);
  const legal = rotated.map((direction, order) => ({
    x: enemy.x + direction.dx,
    y: enemy.y + direction.dy,
    direction,
    order,
    visits: enemy.visits.get(keyFor(enemy.x + direction.dx, enemy.y + direction.dy)) || 0,
  })).filter((cell) => canMoveEnemy(game, enemy, cell.x, cell.y));
  legal.sort((left, right) => left.visits - right.visits || left.order - right.order);
  if (legal.length === 0) return null;
  enemy.heading = DIRECTIONS.indexOf(legal[0].direction);
  return legal[0];
}

function chooseEnemyAction(game, enemy) {
  const line = lineOfFire(game, enemy.x, enemy.y, game.player.x, game.player.y);
  const distance = Math.abs(enemy.x - game.player.x) + Math.abs(enemy.y - game.player.y);
  if (enemy.persona === "AGGRESSIVE") {
    if (line && enemy.ammo > 0) return { type: "SHOOT", direction: line.direction };
    return { type: "MOVE", target: pathStep(game, enemy, true) };
  }
  if (enemy.persona === "CAUTIOUS") {
    if (line && enemy.ammo >= 2) return { type: "SHOOT", direction: line.direction };
    if (distance <= 6) return { type: "MOVE", target: pathStep(game, enemy, false) };
    if ((game.tick & 1) === 0) return { type: "WAIT" };
    return { type: "MOVE", target: pathStep(game, enemy, true) };
  }
  if (line && line.range <= 2 && enemy.ammo > 0) return { type: "SHOOT", direction: line.direction };
  return { type: "MOVE", target: explorerStep(game, enemy) };
}

function directionByName(name) {
  return DIRECTIONS.find((direction) => direction.name === name);
}

function damageEnemy(game, enemy) {
  enemy.hp = Math.max(0, enemy.hp - 1);
  if (enemy.hp === 0) enemy.alive = false;
  game.lastEvent = "HIT";
}

function damagePlayer(game) {
  game.player.hp = Math.max(0, game.player.hp - 1);
  game.lastEvent = "DAMAGE";
  playSound("DAMAGE");
}

function advanceBullets(game) {
  const survivors = [];
  for (const bullet of game.bullets) {
    const x = bullet.x + bullet.dx;
    const y = bullet.y + bullet.dy;
    if (!isWalkable(game.map, x, y)) continue;
    if (bullet.owner === "PLAYER") {
      const enemy = game.enemies.find((candidate) => candidate.alive && candidate.x === x && candidate.y === y);
      if (enemy) { damageEnemy(game, enemy); continue; }
    } else if (game.player.x === x && game.player.y === y) {
      damagePlayer(game);
      continue;
    }
    survivors.push({ ...bullet, x, y });
  }
  game.bullets = survivors;
}

function fireBullet(game, shooter, direction, owner) {
  if (!shooter.alive || shooter.ammo <= 0 || !direction) return false;
  shooter.ammo -= 1;
  const x = shooter.x + direction.dx;
  const y = shooter.y + direction.dy;
  if (owner === "PLAYER") {
    game.lastEvent = "PLAYER_SHOT";
    playSound("PLAYER_SHOT");
  } else {
    const heard = Math.max(Math.abs(shooter.x - game.player.x), Math.abs(shooter.y - game.player.y)) <= 3;
    if (heard) playSound("ENEMY_SHOT");
  }
  if (!isWalkable(game.map, x, y)) return true;
  if (owner === "PLAYER") {
    const enemy = game.enemies.find((candidate) => candidate.alive && candidate.x === x && candidate.y === y);
    if (enemy) { damageEnemy(game, enemy); return true; }
  } else if (game.player.x === x && game.player.y === y) {
    damagePlayer(game);
    return true;
  }
  game.bullets.push({ x, y, dx: direction.dx, dy: direction.dy, owner });
  return true;
}

function recoverAmmo(entity, ammoAtTickStart) {
  if (!entity.alive) return;
  if (ammoAtTickStart >= 3) {
    entity.recharge = 0;
    return;
  }
  if (entity.ammo >= 3) {
    entity.recharge = 0;
    return;
  }
  entity.recharge += 1;
  if (entity.recharge >= 2) {
    entity.ammo += 1;
    entity.recharge = 0;
  }
}

function resolveTick() {
  if (state.mode !== MODE.PLAYING || !state.game) return;
  const game = state.game;
  game.lastEvent = "";
  const playerAmmoAtStart = game.player.ammo;
  const enemyAmmoAtStart = game.enemies.map((enemy) => enemy.ammo);
  const action = game.queue.shift() || { type: "WAIT" };
  const enemyActions = game.enemies.map((enemy) => enemy.alive ? chooseEnemyAction(game, enemy) : { type: "WAIT" });

  if (action.type === "MOVE") {
    const direction = directionByName(action.direction);
    const x = game.player.x + direction.dx;
    const y = game.player.y + direction.dy;
    if (canMovePlayer(game, x, y)) { game.player.x = x; game.player.y = y; }
  }

  enemyActions.forEach((enemyAction, index) => {
    const enemy = game.enemies[index];
    if (!enemy.alive || enemyAction.type !== "MOVE" || !enemyAction.target) return;
    if (canMoveEnemy(game, enemy, enemyAction.target.x, enemyAction.target.y)) {
      enemy.x = enemyAction.target.x;
      enemy.y = enemyAction.target.y;
      const key = keyFor(enemy.x, enemy.y);
      enemy.visits.set(key, (enemy.visits.get(key) || 0) + 1);
    }
  });

  advanceBullets(game);
  if (action.type === "SHOOT") {
    fireBullet(game, game.player, directionByName(action.direction), "PLAYER");
  }
  enemyActions.forEach((enemyAction, index) => {
    if (enemyAction.type === "SHOOT") {
      fireBullet(game, game.enemies[index], enemyAction.direction, `ENEMY_${index}`);
    }
  });

  recoverAmmo(game.player, playerAmmoAtStart);
  game.enemies.forEach((enemy, index) => recoverAmmo(enemy, enemyAmmoAtStart[index]));
  game.tick += 1;

  if (game.player.hp <= 0) finishGame("DEFEAT");
  else if (game.player.x === game.exit.x && game.player.y === game.exit.y) finishGame("VICTORY");
  else if (game.tick >= game.maxTicks) finishGame("TIMEOUT");
  render();
}

function finishGame(result) {
  state.game.result = result;
  state.mode = MODE.RESULT;
  state.resultFocus = 0;
  state.nextTickAt = Number.POSITIVE_INFINITY;
  if (result === "VICTORY") playSound("VICTORY");
  else playSound("DEATH");
}

function enqueueDirection(directionName) {
  const game = state.game;
  if (!game || game.queue.length >= QUEUE_CAPACITY) return;
  game.queue.push({
    type: inputState.firePressed ? "SHOOT" : "MOVE",
    direction: directionName,
  });
}

function noteActivity() {
  state.lastActivity = performance.now();
}

function enterIdle() {
  state.mode = MODE.IDLE;
  state.game = null;
  state.idleSince = performance.now();
  state.lastEyeFrame = "";
  state.nextTickAt = Number.POSITIVE_INFINITY;
  render();
}

function enterHome() {
  state.mode = MODE.HOME;
  state.homeFocus = 0;
  state.game = null;
  state.nextTickAt = Number.POSITIVE_INFINITY;
  render();
}

function dispatch(input) {
  ensureAudio();
  noteActivity();

  if (state.mode === MODE.IDLE) {
    enterHome();
    return;
  }

  if (state.mode === MODE.HOME) {
    if (input === "UP") state.homeFocus = wrapIndex(state.homeFocus - 1, 4);
    if (input === "DOWN") state.homeFocus = wrapIndex(state.homeFocus + 1, 4);
    if (input === "FIRE") {
      if (state.homeFocus === 0) startGame();
      if (state.homeFocus === 1) { state.mode = MODE.SETUP; state.setupFocus = 0; }
      if (state.homeFocus === 2) { state.mode = MODE.SYSTEM; state.systemFocus = 0; }
      if (state.homeFocus === 3) state.mode = MODE.ABOUT;
    }
    if (input === "CLEAR_LONG") enterIdle();
    render();
    return;
  }

  if (state.mode === MODE.SETUP) {
    if (input === "UP") state.setupFocus = wrapIndex(state.setupFocus - 1, 2);
    if (input === "DOWN") state.setupFocus = wrapIndex(state.setupFocus + 1, 2);
    if ((input === "LEFT" || input === "RIGHT") && state.setupFocus === 0) {
      const index = MAP_PRESETS.indexOf(state.pendingMapSize);
      state.pendingMapSize = MAP_PRESETS[wrapIndex(index + (input === "RIGHT" ? 1 : -1), MAP_PRESETS.length)];
    }
    if (input === "FIRE") {
      if (state.setupFocus === 0) {
        const index = MAP_PRESETS.indexOf(state.pendingMapSize);
        state.pendingMapSize = MAP_PRESETS[wrapIndex(index + 1, MAP_PRESETS.length)];
      } else startGame();
    }
    if (input === "CLEAR_SHORT") { state.mode = MODE.HOME; state.homeFocus = 1; }
    if (input === "CLEAR_LONG") enterIdle();
    render();
    return;
  }

  if (state.mode === MODE.SYSTEM) {
    if (input === "UP") state.systemFocus = wrapIndex(state.systemFocus - 1, 3);
    if (input === "DOWN") state.systemFocus = wrapIndex(state.systemFocus + 1, 3);
    if (input === "CLEAR_SHORT") { state.mode = MODE.HOME; state.homeFocus = 2; }
    if (input === "CLEAR_LONG") enterIdle();
    render();
    return;
  }

  if (state.mode === MODE.ABOUT) {
    if (input === "CLEAR_SHORT") { state.mode = MODE.HOME; state.homeFocus = 3; }
    if (input === "CLEAR_LONG") enterIdle();
    render();
    return;
  }

  if (state.mode === MODE.PLAYING) {
    if (DIRECTIONS.some((direction) => direction.name === input)) enqueueDirection(input);
    if (input === "CLEAR_SHORT" && state.game) state.game.queue.length = 0;
    if (input === "CLEAR_LONG") {
      state.mode = MODE.PAUSED;
      state.pauseFocus = 0;
      state.nextTickAt = Number.POSITIVE_INFINITY;
    }
    render();
    return;
  }

  if (state.mode === MODE.PAUSED) {
    if (input === "UP") state.pauseFocus = wrapIndex(state.pauseFocus - 1, 3);
    if (input === "DOWN") state.pauseFocus = wrapIndex(state.pauseFocus + 1, 3);
    if (input === "CLEAR_SHORT") {
      state.mode = MODE.PLAYING;
      state.nextTickAt = performance.now() + TICK_MS;
    }
    if (input === "FIRE") {
      if (state.pauseFocus === 0) {
        state.mode = MODE.PLAYING;
        state.nextTickAt = performance.now() + TICK_MS;
      } else if (state.pauseFocus === 1) startGame(true);
      else { state.mode = MODE.CONFIRM_HOME; state.confirmFocus = 0; }
    }
    render();
    return;
  }

  if (state.mode === MODE.CONFIRM_HOME) {
    if (input === "UP" || input === "DOWN") state.confirmFocus = 1 - state.confirmFocus;
    if (input === "CLEAR_SHORT") state.mode = MODE.PAUSED;
    if (input === "FIRE") {
      if (state.confirmFocus === 0) state.mode = MODE.PAUSED;
      else enterHome();
    }
    render();
    return;
  }

  if (state.mode === MODE.PROMPT) {
    if (input === "UP" || input === "DOWN") state.promptFocus = 1 - state.promptFocus;
    if (input === "CLEAR_SHORT") {
      state.mode = state.previousMode;
      if (state.mode === MODE.PLAYING) state.nextTickAt = performance.now() + TICK_MS;
    }
    if (input === "FIRE") {
      if (state.promptFocus === 0) {
        state.mode = state.previousMode;
        if (state.mode === MODE.PLAYING) state.nextTickAt = performance.now() + TICK_MS;
      } else enterIdle();
    }
    render();
    return;
  }

  if (state.mode === MODE.RESULT) {
    if (input === "UP") state.resultFocus = wrapIndex(state.resultFocus - 1, 3);
    if (input === "DOWN") state.resultFocus = wrapIndex(state.resultFocus + 1, 3);
    if (input === "FIRE") {
      if (state.resultFocus === 0) startGame(true);
      if (state.resultFocus === 1) startGame(false);
      if (state.resultFocus === 2) enterHome();
    }
    if (input === "CLEAR_SHORT") enterHome();
    if (input === "CLEAR_LONG") enterIdle();
    render();
  }
}

function eyeFrame(elapsed) {
  const phase = elapsed % 24000;
  if (phase < 3300) return "NEUTRAL";
  if (phase < 3420) return "BLINK_HALF";
  if (phase < 3540) return "BLINK_CLOSED";
  if (phase < 3660) return "BLINK_HALF";
  if (phase < 7000) return "LOOK_RIGHT";
  if (phase < 9100) return "CURIOUS";
  if (phase < 11000) return "HAPPY";
  if (phase < 13400) return "NEUTRAL";
  if (phase < 13520) return "BLINK_HALF";
  if (phase < 13640) return "BLINK_CLOSED";
  if (phase < 13760) return "BLINK_HALF";
  if (phase < 16900) return "LOOK_LEFT";
  if (phase < 19000) return "SURPRISED";
  if (phase < 21800) return "SLEEPY";
  return "NEUTRAL";
}

function drawOpenEye(context, pupilOffset = 0, width = 76, height = 36) {
  const left = Math.round((128 - width) / 2);
  const top = Math.round((64 - height) / 2);
  fillRect(context, left + 8, top, width - 16, 3);
  fillRect(context, left + 3, top + 3, 7, 3);
  fillRect(context, left, top + 6, 3, height - 12);
  fillRect(context, left + width - 3, top + 6, 3, height - 12);
  fillRect(context, left + 3, top + height - 6, 7, 3);
  fillRect(context, left + 8, top + height - 3, width - 16, 3);
  const pupilX = Math.max(left + 10, Math.min(left + width - 24, 58 + pupilOffset));
  fillRect(context, pupilX, top + 9, 12, height - 18);
  fillRect(context, pupilX + 3, top + 12, 3, 3, false);
}

function drawEye(context, frame, rightEye) {
  clearCanvas(context);
  if (frame === "BLINK_CLOSED") {
    drawLine(context, 30, 31, 48, 36);
    drawLine(context, 48, 36, 64, 38);
    drawLine(context, 64, 38, 80, 36);
    drawLine(context, 80, 36, 98, 31);
    return;
  }
  if (frame === "HAPPY") {
    drawLine(context, 26, 38, 40, 27);
    drawLine(context, 40, 27, 64, 22);
    drawLine(context, 64, 22, 88, 27);
    drawLine(context, 88, 27, 102, 38);
    drawLine(context, 27, 40, 41, 30);
    drawLine(context, 41, 30, 64, 25);
    drawLine(context, 64, 25, 87, 30);
    drawLine(context, 87, 30, 101, 40);
    return;
  }
  if (frame === "SLEEPY" || frame === "BLINK_HALF") {
    fillRect(context, 27, frame === "SLEEPY" ? 31 : 27, 74, 3);
    fillRect(context, 30, frame === "SLEEPY" ? 34 : 30, 68, 10);
    fillRect(context, 36, frame === "SLEEPY" ? 41 : 40, 56, 3);
    return;
  }
  if (frame === "SURPRISED") {
    drawOpenEye(context, 0, 48, 48);
    return;
  }
  if (frame === "CURIOUS") {
    drawOpenEye(context, rightEye ? 2 : -2, rightEye ? 80 : 64, rightEye ? 38 : 30);
    return;
  }
  const offset = frame === "LOOK_LEFT" ? -18 : frame === "LOOK_RIGHT" ? 18 : 0;
  drawOpenEye(context, offset);
}

function drawHome() {
  clearCanvas(contexts.map);
  clearCanvas(contexts.hud);
  drawText(contexts.map, 4, 2, "CATAMAZE");
  fillRect(contexts.map, 4, 11, 120, 1);
  ["PLAY", "MAP SETUP", "SYSTEM", "ABOUT"].forEach((label, index) => {
    drawMenuRow(contexts.map, 17 + index * 11, label, state.homeFocus === index);
  });

  if (state.homeFocus === 0) {
    drawText(contexts.hud, 4, 3, "NEW RUN");
    drawText(contexts.hud, 4, 16, `MAP    ${state.pendingMapSize}X${state.pendingMapSize}`);
    drawText(contexts.hud, 4, 27, `LIMIT  ${tickBudget(state.pendingMapSize)}`);
    drawText(contexts.hud, 4, 38, "PLAYER 9X5");
    drawText(contexts.hud, 4, 49, "AI     5X5");
  } else if (state.homeFocus === 1) {
    drawText(contexts.hud, 4, 3, "MAP PRESET");
    drawText(contexts.hud, 4, 18, "4 SIZES");
    drawText(contexts.hud, 4, 30, "12 / 20 / 30 / 50");
    drawText(contexts.hud, 4, 44, "FIRE TO EDIT");
  } else if (state.homeFocus === 2) {
    drawText(contexts.hud, 4, 3, "SYSTEM");
    drawText(contexts.hud, 4, 18, "LOCAL BROWSER");
    drawText(contexts.hud, 4, 30, "NO BACKEND");
    drawText(contexts.hud, 4, 42, "SOUND OPTIONAL");
  } else {
    drawText(contexts.hud, 4, 3, "TWO MODES");
    drawText(contexts.hud, 4, 18, "MAZE GAME");
    drawText(contexts.hud, 4, 30, "DESK COMPANION");
    drawText(contexts.hud, 4, 46, "V1 SHOWCASE");
  }
}

function drawSetup() {
  clearCanvas(contexts.map);
  clearCanvas(contexts.hud);
  drawText(contexts.map, 4, 3, "MAP SETUP");
  fillRect(contexts.map, 4, 12, 120, 1);
  drawMenuRow(contexts.map, 20, `SIZE ${state.pendingMapSize}X${state.pendingMapSize}`, state.setupFocus === 0);
  drawMenuRow(contexts.map, 34, "START GAME", state.setupFocus === 1);
  drawText(contexts.map, 4, 53, "LEFT/RIGHT EDIT");

  const names = { 12: "QUICK", 20: "COMPACT", 30: "CLASSIC", 50: "MARATHON" };
  drawText(contexts.hud, 4, 3, names[state.pendingMapSize]);
  drawText(contexts.hud, 4, 17, `SIZE   ${state.pendingMapSize}X${state.pendingMapSize}`);
  drawText(contexts.hud, 4, 28, `LIMIT  ${tickBudget(state.pendingMapSize)}`);
  drawText(contexts.hud, 4, 39, "ENEMY  3");
  drawText(contexts.hud, 4, 50, "AI FOV 5X5");
}

function drawSystem() {
  clearCanvas(contexts.map);
  clearCanvas(contexts.hud);
  drawText(contexts.map, 4, 3, "SYSTEM");
  ["HARDWARE", "SOFTWARE", "CONTROLS"].forEach((label, index) => {
    drawMenuRow(contexts.map, 19 + index * 13, label, state.systemFocus === index);
  });
  if (state.systemFocus === 0) {
    drawText(contexts.hud, 4, 3, "PRODUCT TWIN");
    drawText(contexts.hud, 4, 18, "2 X 128X64 OLED");
    drawText(contexts.hud, 4, 31, "ESP32-S3 OFFLINE");
    drawText(contexts.hud, 4, 47, "THIS: BROWSER SIM");
  } else if (state.systemFocus === 1) {
    drawText(contexts.hud, 4, 3, "RELEASE");
    drawText(contexts.hud, 4, 18, RELEASE.replaceAll(".", "-"));
    drawText(contexts.hud, 4, 31, "600MS TICK");
    drawText(contexts.hud, 4, 47, "STATIC / OFFLINE");
  } else {
    drawText(contexts.hud, 4, 3, "SIX BUTTONS");
    drawText(contexts.hud, 4, 18, "ARROWS MOVE");
    drawText(contexts.hud, 4, 31, "FIRE + DIR SHOOT");
    drawText(contexts.hud, 4, 47, "HOLD CLEAR PAUSE");
  }
}

function drawAbout() {
  clearCanvas(contexts.map);
  clearCanvas(contexts.hud);
  drawRect(contexts.map, 2, 2, 124, 60);
  drawText(contexts.map, 19, 13, "CATAMAZE");
  drawText(contexts.map, 13, 30, "GAME + COMPANION");
  drawText(contexts.map, 31, 47, "HACKUMASS");
  drawText(contexts.hud, 4, 3, "PLAYER ADVANTAGE");
  drawText(contexts.hud, 4, 19, "PLAYER VIEW  9X5");
  drawText(contexts.hud, 4, 32, "EACH AI VIEW 5X5");
  drawText(contexts.hud, 4, 49, "CLEAR TO RETURN");
}

function hasLineOfSight(game, targetX, targetY) {
  let x0 = game.player.x;
  let y0 = game.player.y;
  const x1 = targetX;
  const y1 = targetY;
  const dx = Math.abs(x1 - x0);
  const sx = x0 < x1 ? 1 : -1;
  const dy = -Math.abs(y1 - y0);
  const sy = y0 < y1 ? 1 : -1;
  let error = dx + dy;
  while (!(x0 === x1 && y0 === y1)) {
    const doubled = 2 * error;
    if (doubled >= dy) { error += dy; x0 += sx; }
    if (doubled <= dx) { error += dx; y0 += sy; }
    if (x0 === x1 && y0 === y1) return true;
    if (!inBounds(game.map, x0, y0) || game.map[y0][x0] === "#") return false;
  }
  return true;
}

function drawPlayerDiamond(context, x, y) {
  const points = [[6, 1], [5, 2], [7, 2], [4, 3], [8, 3], [3, 4], [9, 4], [2, 5],
    [10, 5], [2, 6], [10, 6], [3, 7], [9, 7], [4, 8], [8, 8], [5, 9], [7, 9], [6, 10]];
  points.forEach(([dx, dy]) => pixel(context, x + dx, y + dy));
}

function drawMap() {
  const game = state.game;
  clearCanvas(contexts.map);
  if (!game) return;
  for (let row = 0; row < 5; row += 1) {
    for (let column = 0; column < 9; column += 1) {
      const worldX = game.player.x + column - 4;
      const worldY = game.player.y + row - 2;
      const x = 10 + column * 12;
      const y = 2 + row * 12;
      const visible = inBounds(game.map, worldX, worldY) && hasLineOfSight(game, worldX, worldY);
      if (!visible) {
        for (let offset = 0; offset < 7; offset += 1) pixel(contexts.map, x + 3 + offset, y + 9 - offset);
      } else if (game.map[worldY][worldX] === "#") {
        fillRect(contexts.map, x, y, 12, 12);
      } else if (game.map[worldY][worldX] === "S" || game.map[worldY][worldX] === "E") {
        drawChar(contexts.map, x + 3, y + 2, game.map[worldY][worldX]);
      }
      if (column === 4 && row === 2) {
        drawPlayerDiamond(contexts.map, x, y);
      } else if (visible && game.enemies.some((enemy) => enemy.alive && enemy.x === worldX && enemy.y === worldY)) {
        fillRect(contexts.map, x + 3, y + 3, 6, 6);
      }
    }
  }
}

function drawHud() {
  const game = state.game;
  clearCanvas(contexts.hud);
  if (!game) return;
  drawText(contexts.hud, 1, 3, "TICK");
  drawText(contexts.hud, 44, 3, pad(game.tick, 5));
  drawText(contexts.hud, 1, 15, "HP");
  for (let index = 0; index < 5; index += 1) {
    drawIcon(contexts.hud, 44 + index * 9, 15, index < game.player.hp ? HEART_FILLED : HEART_OUTLINE);
  }
  drawText(contexts.hud, 1, 27, "AMMO");
  for (let index = 0; index < 3; index += 1) {
    drawIcon(contexts.hud, 44 + index * 10, 27, index < game.player.ammo ? AMMO_FILLED : AMMO_OUTLINE);
  }
  drawText(contexts.hud, 1, 39, "QUEUE");
  drawText(contexts.hud, 44, 39, `${pad(game.queue.length, 2)}/32`);
  drawText(contexts.hud, 1, 51, "POS");
  drawText(contexts.hud, 44, 51, `${pad(game.player.x, 2)},${pad(game.player.y, 2)}`);
}

function drawPause() {
  drawMap();
  clearCanvas(contexts.hud);
  drawText(contexts.hud, 4, 3, "PAUSED");
  ["RESUME", "RESTART", "HOME"].forEach((label, index) => {
    drawMenuRow(contexts.hud, 20 + index * 12, label, state.pauseFocus === index);
  });
}

function drawConfirmHome() {
  drawMap();
  clearCanvas(contexts.hud);
  drawText(contexts.hud, 4, 4, "LEAVE RUN?");
  drawText(contexts.hud, 4, 16, "QUEUE IS UNSAVED");
  ["CANCEL", "LEAVE"].forEach((label, index) => {
    drawMenuRow(contexts.hud, 33 + index * 13, label, state.confirmFocus === index);
  });
}

function drawPrompt() {
  drawMap();
  clearCanvas(contexts.hud);
  drawText(contexts.hud, 4, 3, "STILL THERE?");
  drawText(contexts.hud, 4, 15, "WORLD IS FROZEN");
  ["CONTINUE", "SLEEP"].forEach((label, index) => {
    drawMenuRow(contexts.hud, 32 + index * 13, label, state.promptFocus === index);
  });
}

function drawResult() {
  drawMap();
  clearCanvas(contexts.hud);
  drawText(contexts.hud, 4, 2, state.game?.result || "RESULT");
  drawText(contexts.hud, 4, 12, `TICK ${pad(state.game?.tick || 0, 5)}`);
  ["REPLAY", "NEW RUN", "HOME"].forEach((label, index) => {
    drawMenuRow(contexts.hud, 27 + index * 11, label, state.resultFocus === index);
  });
}

function currentStatus() {
  if (state.mode === MODE.IDLE) return `IDLE / ${state.lastEyeFrame || "NEUTRAL"}`;
  if (state.mode === MODE.PROMPT) return "PAUSED / INACTIVE";
  if (state.mode === MODE.CONFIRM_HOME) return "PAUSED / CONFIRM";
  return state.mode;
}

function render() {
  if (state.mode === MODE.IDLE) {
    const frame = eyeFrame(performance.now() - state.idleSince);
    state.lastEyeFrame = frame;
    drawEye(contexts.map, frame, false);
    drawEye(contexts.hud, frame, true);
  } else if (state.mode === MODE.HOME) drawHome();
  else if (state.mode === MODE.SETUP) drawSetup();
  else if (state.mode === MODE.SYSTEM) drawSystem();
  else if (state.mode === MODE.ABOUT) drawAbout();
  else if (state.mode === MODE.PLAYING) { drawMap(); drawHud(); }
  else if (state.mode === MODE.PAUSED) drawPause();
  else if (state.mode === MODE.CONFIRM_HOME) drawConfirmHome();
  else if (state.mode === MODE.PROMPT) drawPrompt();
  else if (state.mode === MODE.RESULT) drawResult();

  elements.status.textContent = currentStatus();
  elements.tick.textContent = pad(state.game?.tick || 0, 5);
  elements.queue.textContent = `${pad(state.game?.queue.length || 0, 2)}/32`;
}

function ensureAudio() {
  if (!state.audioEnabled) return;
  const AudioContext = window.AudioContext || window.webkitAudioContext;
  if (!AudioContext) return;
  if (!state.audioContext) state.audioContext = new AudioContext();
  if (state.audioContext.state === "suspended") state.audioContext.resume().catch(() => {});
}

function tone(frequency, duration, offset = 0, volume = 0.025) {
  const context = state.audioContext;
  if (!state.audioEnabled || !context || context.state !== "running") return;
  const oscillator = context.createOscillator();
  const gain = context.createGain();
  const start = context.currentTime + 0.008 + offset;
  oscillator.type = "square";
  oscillator.frequency.setValueAtTime(frequency, start);
  gain.gain.setValueAtTime(volume, start);
  gain.gain.exponentialRampToValueAtTime(0.0001, start + duration);
  oscillator.connect(gain);
  gain.connect(context.destination);
  oscillator.start(start);
  oscillator.stop(start + duration);
}

function playSound(event) {
  if (event === "PLAYER_SHOT") tone(120, 0.075, 0, 0.035);
  if (event === "ENEMY_SHOT") { tone(84, 0.04); tone(64, 0.04, 0.075); }
  if (event === "DAMAGE") { tone(58, 0.09, 0, 0.04); tone(44, 0.11, 0.13, 0.04); }
  if (event === "VICTORY") { tone(440, 0.08); tone(660, 0.08, 0.12); tone(880, 0.14, 0.24); }
  if (event === "DEATH") tone(52, 0.42, 0, 0.04);
}

function beginFire() {
  if (inputState.firePressed) return;
  ensureAudio();
  inputState.firePressed = true;
  inputState.fireWakeConsumed = state.mode === MODE.IDLE;
  elements.fire.classList.add("active");
  if (inputState.fireWakeConsumed) dispatch("FIRE");
}

function releaseFire(commit) {
  if (!inputState.firePressed) return;
  const shouldCommit = commit && !inputState.fireWakeConsumed;
  inputState.firePressed = false;
  inputState.fireWakeConsumed = false;
  elements.fire.classList.remove("active");
  if (shouldCommit) dispatch("FIRE");
}

function beginClear() {
  if (inputState.clearPressed) return;
  ensureAudio();
  inputState.clearPressed = true;
  inputState.clearLongCommitted = false;
  inputState.clearWakeConsumed = state.mode === MODE.IDLE;
  elements.clear.classList.add("active");
  if (inputState.clearWakeConsumed) {
    dispatch("CLEAR_SHORT");
    return;
  }
  elements.clear.classList.add("charging");
  inputState.clearTimer = window.setTimeout(() => {
    if (!inputState.clearPressed || inputState.clearLongCommitted) return;
    inputState.clearLongCommitted = true;
    elements.clear.classList.remove("charging");
    dispatch("CLEAR_LONG");
  }, CLEAR_LONG_MS);
}

function releaseClear(commit) {
  if (!inputState.clearPressed) return;
  window.clearTimeout(inputState.clearTimer);
  const shouldCommit = commit && !inputState.clearLongCommitted && !inputState.clearWakeConsumed;
  inputState.clearPressed = false;
  inputState.clearLongCommitted = false;
  inputState.clearWakeConsumed = false;
  inputState.clearTimer = null;
  elements.clear.classList.remove("active", "charging");
  if (shouldCommit) dispatch("CLEAR_SHORT");
}

document.querySelectorAll("[data-direction]").forEach((button) => {
  button.addEventListener("pointerdown", (event) => {
    event.preventDefault();
    button.setPointerCapture(event.pointerId);
    button.classList.add("active");
    dispatch(button.dataset.direction);
  });
  const release = () => button.classList.remove("active");
  button.addEventListener("pointerup", release);
  button.addEventListener("pointercancel", release);
  button.addEventListener("lostpointercapture", release);
});

elements.fire.addEventListener("pointerdown", (event) => {
  event.preventDefault();
  elements.fire.setPointerCapture(event.pointerId);
  beginFire();
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

elements.sound.addEventListener("click", () => {
  state.audioEnabled = !state.audioEnabled;
  elements.sound.setAttribute("aria-pressed", String(state.audioEnabled));
  elements.sound.textContent = state.audioEnabled ? "SOUND ON" : "SOUND OFF";
  if (state.audioEnabled) ensureAudio();
});

const KEY_DIRECTIONS = new Map([
  ["ArrowUp", "UP"], ["ArrowRight", "RIGHT"], ["ArrowDown", "DOWN"], ["ArrowLeft", "LEFT"],
]);

window.addEventListener("keydown", (event) => {
  if (event.repeat) return;
  if (event.code === "Space") {
    event.preventDefault();
    beginFire();
    return;
  }
  const direction = KEY_DIRECTIONS.get(event.key);
  if (direction) {
    event.preventDefault();
    dispatch(direction);
    return;
  }
  if (event.key.toLowerCase() === "c") {
    event.preventDefault();
    beginClear();
  }
});

window.addEventListener("keyup", (event) => {
  if (event.code === "Space") releaseFire(true);
  if (event.key.toLowerCase() === "c") releaseClear(true);
});

window.addEventListener("blur", () => {
  releaseFire(false);
  releaseClear(false);
  document.querySelectorAll(".key.active").forEach((button) => button.classList.remove("active"));
});

function checkInactivity(now) {
  if (state.mode === MODE.IDLE || state.mode === MODE.PROMPT || state.mode === MODE.CONFIRM_HOME) return;
  if (now - state.lastActivity < INACTIVITY_MS) return;
  if (state.mode === MODE.PLAYING || state.mode === MODE.PAUSED) {
    state.previousMode = state.mode;
    state.mode = MODE.PROMPT;
    state.promptFocus = 0;
    state.nextTickAt = Number.POSITIVE_INFINITY;
    state.lastActivity = now;
    render();
  } else {
    enterIdle();
  }
}

function animationLoop(now) {
  if (state.mode === MODE.PLAYING && now >= state.nextTickAt) {
    resolveTick();
    state.nextTickAt = now + TICK_MS;
  }
  checkInactivity(now);
  if (state.mode === MODE.IDLE) {
    const frame = eyeFrame(now - state.idleSince);
    if (frame !== state.lastEyeFrame) render();
  }
  window.requestAnimationFrame(animationLoop);
}

function snapshot() {
  return {
    release: RELEASE,
    runtime: "BROWSER_SIM",
    mode: state.mode,
    previousMode: state.previousMode,
    mapSize: state.mapSize,
    pendingMapSize: state.pendingMapSize,
    tick: state.game?.tick || 0,
    queue: state.game?.queue.map((action) => `${action.type}_${action.direction || ""}`) || [],
    player: state.game ? {
      x: state.game.player.x,
      y: state.game.player.y,
      hp: state.game.player.hp,
      ammo: state.game.player.ammo,
    } : null,
    result: state.game?.result || "",
    eyeFrame: state.lastEyeFrame,
    soundEnabled: state.audioEnabled,
  };
}

window.__CATAMAZE_SHOWCASE__ = Object.freeze({
  snapshot,
  step() { resolveTick(); return snapshot(); },
  forceInactivity() {
    state.lastActivity = performance.now() - INACTIVITY_MS - 1;
    checkInactivity(performance.now());
    return snapshot();
  },
  reset() {
    state.pendingMapSize = 30;
    state.runCounter = 0;
    enterIdle();
    return snapshot();
  },
});

render();
window.requestAnimationFrame(animationLoop);
