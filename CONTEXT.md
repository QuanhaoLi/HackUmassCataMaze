<!--
Created at: 2026-11-14 06:54 EST
Created by: Codex
Last Modified at: 2026-11-14 11:27 EST
Last Modified by: Codex

本文档是 CataMaze 产品领域语言词汇表，不包含实现规格。
-->

# CataMaze Product Context

CataMaze is a dual-purpose desktop companion and handheld maze game whose Companion Idle, launcher, setup flow, Game Session, and pause flow share six physical buttons across two monochrome screens.

## Language

**Home**:
The top-level launcher from which the player starts a game, changes setup, or opens system information.
_Avoid_: Main screen, start page, desktop

**Companion Idle**:
The resting product mode in which the two physical screens form one expressive pair of eyes and no Game Session exists.
_Avoid_: Home, sleep screen, attract mode

**Wake**:
The consumed first button intent that leaves Companion Idle and reveals Home without also navigating, confirming, moving, or shooting.
_Avoid_: Start game, resume

**Inactivity Prompt**:
The confirmation shown after 30 seconds without button activity during a live or paused Game Session; it freezes the session and offers Continue or Sleep.
_Avoid_: Pause Menu, timeout, idle screen

**Sleep**:
The confirmed abandonment of a Game Session from Inactivity Prompt, or the automatic transition from an inactive non-game menu, into Companion Idle.
_Avoid_: Pause, Home, power off

**Setup**:
The pre-game flow where the player chooses the next Game Session's configuration.
_Avoid_: Options, settings, configuration page

**Game Session**:
One run from maze creation until victory, death, timeout, restart, or abandonment to Home.
_Avoid_: Match, level, app

**Pause Menu**:
The in-session menu that suspends world progression while preserving the current Game Session and its Action Queue.
_Avoid_: Home, Setup, system menu

**Action Queue**:
The ordered player intents that have been accepted but not yet executed by a game tick.
_Avoid_: Input buffer, command list

**Wait Action**:
The domain action executed when the Action Queue is empty or when an AI has no available action. It has no dedicated physical button.
_Avoid_: WAIT button, idle command

**CLEAR Short Press**:
A CLEAR gesture released before 800 ms. It removes pending Action Queue entries during a Game Session and returns one level in system menus.
_Avoid_: Pause, Home shortcut

**CLEAR Long Press**:
A CLEAR gesture committed once at 800 ms. It opens Pause Menu during a Game Session and returns directly to Home from pre-game system menus without emitting a later short press.
_Avoid_: Queue clear, reset, quit

**Resume**:
The transition from Pause Menu back to the same preserved Game Session.
_Avoid_: Start, continue game from save

**Restart**:
The end of the current Game Session followed by a new session using the same confirmed Setup and seed.
_Avoid_: Resume, retry with new map

**Map Preset**:
One of the reviewed square world sizes—Tiny, Small, Medium, or Original—captured by a Game Session when it starts.
_Avoid_: Resolution, difficulty, arbitrary map size

**Tick Budget**:
The maximum completed ticks allowed for a Game Session, derived from its Map Preset.
_Avoid_: Timer, time limit in seconds

**Six-button set**:
The physical controls UP, DOWN, LEFT, RIGHT, FIRE, and CLEAR shared by navigation and gameplay.
_Avoid_: Seven-button set, WAIT button

## Flagged ambiguities

**WAIT** previously referred to both a physical button and a domain action. The physical WAIT button is removed; only Wait Action remains.

**Home** and **Pause Menu** are not aliases. Home owns pre-game navigation; Pause Menu temporarily suspends one existing Game Session.

**Idle** previously meant either an empty Action Queue or the product resting state. The empty queue produces Wait Action; the product resting state is always called Companion Idle.

## Example dialogue

> **Developer:** What happens when CLEAR is held during a Game Session?
>
> **Domain expert:** It creates a CLEAR Long Press and opens the Pause Menu. The Action Queue stays intact.
>
> **Developer:** And a quick tap?
>
> **Domain expert:** That is CLEAR Short Press; it empties the Action Queue. If the player chooses Resume, the same Game Session continues. Restart creates a new Game Session from the same Setup and seed, while Home abandons the run after confirmation.
>
> **Developer:** Does the button that wakes the companion also select PLAY?
>
> **Domain expert:** No. Wake is consumed and reveals Home. A second deliberate FIRE starts the configured Game Session.
