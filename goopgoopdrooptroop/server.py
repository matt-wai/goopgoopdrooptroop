"""Multiplayer WebSocket server for GoopGoopDroopTroop.

Run with:
    ggdt-server                   (uses default port 8765)
    ggdt-server --port 9000

Protocol (JSON lines over WebSocket):
  Client → Server:
    { "type": "join",    "player_name": "..." }
    { "type": "action",  "action": "..." }        # menu choice
    { "type": "input",   "value": "..." }          # sub-prompt answer
    { "type": "challenge", "target": "player_name" } # PvP challenge
    { "type": "ping" }

  Server → Client:
    { "type": "welcome",  "player_name": "...", "player_id": "..." }
    { "type": "state",    "troop": {...}, "gacha": {...}, "online": [...] }
    { "type": "prompt",   "text": "...", "tag": "..." }  # needs input
    { "type": "message",  "text": "...", "style": "..." }
    { "type": "battle",   "log": [...], "won": bool }
    { "type": "challenge_incoming", "from": "..." }
    { "type": "error",    "text": "..." }
    { "type": "pong" }
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import random
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import websockets
from websockets.server import WebSocketServerProtocol

from .goop import Goop, Troop
from .missions import Mission, run_mission
from .gacha import (
    GachaState, BANNERS, PULL_COST_SINGLE, PULL_COST_TEN,
    RARITY_EMOJI, RARITY_COLORS,
)
from .art import random_goop_name, IDLE_LINES

log = logging.getLogger("ggdt.server")

SERVER_SAVE_DIR = Path.home() / ".goopgoopdrooptroop" / "server"
SERVER_SAVE_DIR.mkdir(parents=True, exist_ok=True)


# ── Player session ────────────────────────────────────────────────────────────

@dataclass
class PlayerSession:
    player_id: str
    player_name: str
    ws: WebSocketServerProtocol
    troop: Troop
    # pending_challenge: who sent us a challenge
    pending_challenge: str | None = None
    # input_queue: for multi-step interactions
    input_queue: asyncio.Queue = field(default_factory=asyncio.Queue)

    def save_path(self) -> Path:
        return SERVER_SAVE_DIR / f"{self.player_id}.json"

    def save(self):
        data = {
            "player_id": self.player_id,
            "player_name": self.player_name,
            "troop": {
                "goop_bucks": self.troop.goop_bucks,
                "total_missions": self.troop.total_missions,
                "reputation": self.troop.reputation,
                "goops": [g.to_dict() for g in self.troop.goops],
                "gacha": self.troop.get_gacha().to_dict(),
            },
        }
        self.save_path().write_text(json.dumps(data, indent=2))

    @staticmethod
    def load_or_create(player_id: str, player_name: str, ws: WebSocketServerProtocol) -> PlayerSession:
        from .gacha import GachaState
        path = SERVER_SAVE_DIR / f"{player_id}.json"
        if path.exists():
            raw = json.loads(path.read_text())
            td = raw["troop"]
            troop = Troop(
                goop_bucks=td["goop_bucks"],
                total_missions=td["total_missions"],
                reputation=td["reputation"],
                gacha=GachaState.from_dict(td.get("gacha", {})),
            )
            troop.goops = [Goop.from_dict(g) for g in td["goops"]]
            name = raw.get("player_name", player_name)
        else:
            troop = Troop()
            name = player_name

        return PlayerSession(
            player_id=player_id,
            player_name=name,
            ws=ws,
            troop=troop,
        )


# ── Server state ──────────────────────────────────────────────────────────────

class GameServer:
    def __init__(self):
        self.sessions: dict[str, PlayerSession] = {}   # player_id → session
        self.name_to_id: dict[str, str] = {}           # player_name → player_id
        self.pvp_battles: set[frozenset[str]] = set()  # active battle pairs

    def online_list(self) -> list[dict]:
        return [
            {"name": s.player_name, "reputation": s.troop.reputation,
             "power": s.troop.troop_power, "goops": len(s.troop.alive_goops)}
            for s in self.sessions.values()
        ]

    async def broadcast(self, msg: dict, exclude_id: str | None = None):
        for pid, session in list(self.sessions.items()):
            if pid == exclude_id:
                continue
            try:
                await session.ws.send(json.dumps(msg))
            except Exception:
                pass

    async def send(self, session: PlayerSession, msg: dict):
        try:
            await session.ws.send(json.dumps(msg))
        except Exception:
            pass

    async def send_state(self, session: PlayerSession):
        gacha = session.troop.get_gacha()
        await self.send(session, {
            "type": "state",
            "troop": {
                "goop_bucks": session.troop.goop_bucks,
                "total_missions": session.troop.total_missions,
                "reputation": session.troop.reputation,
                "troop_power": session.troop.troop_power,
                "goops": [g.to_dict() for g in session.troop.goops],
                "gacha_inventory": gacha.inventory,
                "gacha_pity": gacha.pity_info(),
                "banner": gacha.active_banner.name,
            },
            "online": self.online_list(),
        })

    # ── handlers ─────────────────────────────────────────────────────────────

    async def handle_join(self, ws: WebSocketServerProtocol, msg: dict) -> PlayerSession | None:
        player_name = (msg.get("player_name") or "Anonymous").strip()[:20]
        player_id = msg.get("player_id") or str(uuid.uuid4())

        session = PlayerSession.load_or_create(player_id, player_name, ws)
        session.ws = ws  # ws might have changed on reconnect

        # Ensure unique name
        if player_name in self.name_to_id and self.name_to_id[player_name] != player_id:
            player_name = f"{player_name}_{player_id[:4]}"
            session.player_name = player_name

        # Bootstrap troop if empty
        if not session.troop.goops:
            goop = session.troop.recruit()
            await self.send(session, {
                "type": "message",
                "text": f"Welcome! Your first goop {goop.name} has been recruited!",
                "style": "bold green",
            })

        self.sessions[player_id] = session
        self.name_to_id[player_name] = player_id

        await self.send(session, {
            "type": "welcome",
            "player_name": session.player_name,
            "player_id": player_id,
        })
        await self.send_state(session)
        await self.broadcast({
            "type": "message",
            "text": f"🫠 {player_name} has oozed into the server!",
            "style": "dim",
        }, exclude_id=player_id)
        session.save()
        return session

    async def handle_action(self, session: PlayerSession, action: str):
        troop = session.troop

        # ── Gacha ──────────────────────────────────────────────────────────
        if action == "gacha_single":
            gacha = troop.get_gacha()
            if troop.goop_bucks < PULL_COST_SINGLE:
                await self.send(session, {"type": "error",
                    "text": f"Need {PULL_COST_SINGLE} GoopBucks for a single pull!"})
                return
            troop.goop_bucks -= PULL_COST_SINGLE
            relic = gacha.single_pull()
            await self.send(session, {
                "type": "message",
                "text": (f"{RARITY_EMOJI[relic.rarity]} [{relic.rarity.upper()}] "
                         f"{relic.name}\n{relic.description}\n{relic.stat_line()}"),
                "style": RARITY_COLORS[relic.rarity],
            })

        elif action == "gacha_ten":
            gacha = troop.get_gacha()
            if troop.goop_bucks < PULL_COST_TEN:
                await self.send(session, {"type": "error",
                    "text": f"Need {PULL_COST_TEN} GoopBucks for a 10-pull!"})
                return
            troop.goop_bucks -= PULL_COST_TEN
            relics = gacha.ten_pull()
            lines = []
            for r in relics:
                lines.append(f"  {RARITY_EMOJI[r.rarity]} [{r.rarity.upper()}] {r.name}")
            await self.send(session, {
                "type": "message",
                "text": "=== 10-PULL RESULTS ===\n" + "\n".join(lines) + f"\n\n{gacha.pity_info()}",
                "style": "bold",
            })

        elif action == "gacha_switch_banner":
            await self.send(session, {
                "type": "prompt",
                "text": "\n".join(
                    f"[{i}] {b.name} - {b.description}" for i, b in enumerate(BANNERS)
                ) + "\nChoose banner index:",
                "tag": "banner_select",
            })
            return  # wait for input

        elif action == "gacha_inventory":
            gacha = troop.get_gacha()
            relics = gacha.get_inventory_relics()
            if not relics:
                await self.send(session, {"type": "message",
                    "text": "Your relic inventory is empty. Go pull!", "style": "yellow"})
            else:
                from collections import Counter
                counts: Counter[str] = Counter(r.id for r in relics)
                lines = []
                seen: set[str] = set()
                for r in relics:
                    if r.id not in seen:
                        seen.add(r.id)
                        lines.append(
                            f"{RARITY_EMOJI[r.rarity]} {r.name} x{counts[r.id]}  |  {r.stat_line()}")
                await self.send(session, {"type": "message",
                    "text": "=== RELIC INVENTORY ===\n" + "\n".join(lines),
                    "style": "white"})

        elif action == "gacha_equip":
            await self.send(session, {
                "type": "prompt",
                "text": "Enter: <goop_index> <relic_index> (use inventory command to see indices)",
                "tag": "equip_select",
            })
            return

        # ── Mission ────────────────────────────────────────────────────────
        elif action == "mission":
            if not troop.alive_goops:
                await self.send(session, {"type": "error", "text": "No living goops!"})
                return
            mission = Mission.generate(troop.troop_power)
            squad = troop.alive_goops[:3]  # auto-select top 3 for server mode
            won, log_lines = run_mission(troop, squad, mission)
            await self.send(session, {
                "type": "battle",
                "log": log_lines,
                "won": won,
            })

        # ── Recruit ────────────────────────────────────────────────────────
        elif action == "recruit":
            cost = 20 + len(troop.goops) * 10
            if troop.goop_bucks < cost:
                await self.send(session, {"type": "error",
                    "text": f"Need {cost} GoopBucks to recruit!"})
                return
            goop = troop.recruit()
            await self.send(session, {"type": "message",
                "text": f"🆕 {goop.name} has joined your troop!", "style": "bold green"})

        # ── Tick (feed/train/rest) ─────────────────────────────────────────
        elif action == "feed_all":
            msgs = []
            for g in troop.alive_goops:
                msgs.append(g.feed())
            troop.goop_bucks = max(0, troop.goop_bucks - 5 * len(troop.alive_goops))
            await self.send(session, {"type": "message",
                "text": "\n".join(msgs), "style": "green"})

        elif action == "train_all":
            msgs = []
            for g in troop.alive_goops:
                msgs.append(g.train())
            await self.send(session, {"type": "message",
                "text": "\n".join(msgs), "style": "cyan"})

        elif action == "rest_all":
            msgs = []
            for g in troop.alive_goops:
                msgs.append(g.rest())
            await self.send(session, {"type": "message",
                "text": "\n".join(msgs), "style": "blue"})

        # ── Tick ──────────────────────────────────────────────────────────
        elif action == "tick":
            troop.tick_all()
            idle = random.choice(IDLE_LINES)
            await self.send(session, {"type": "message", "text": idle, "style": "dim italic"})

        await self.send_state(session)
        session.save()

    async def handle_input(self, session: PlayerSession, value: str, tag: str):
        troop = session.troop

        if tag == "banner_select":
            try:
                idx = int(value.strip())
                gacha = troop.get_gacha()
                gacha.active_banner_idx = idx % len(BANNERS)
                await self.send(session, {"type": "message",
                    "text": f"Banner switched to: {gacha.active_banner.name}", "style": "cyan"})
            except ValueError:
                await self.send(session, {"type": "error", "text": "Invalid banner index."})
            await self.send_state(session)
            session.save()

        elif tag == "equip_select":
            try:
                parts = value.strip().split()
                gi, ri = int(parts[0]) - 1, int(parts[1]) - 1
                alive = troop.alive_goops
                gacha = troop.get_gacha()
                relics = gacha.get_inventory_relics()
                # dedupe by unique id
                unique_relics = list({r.id: r for r in relics}.values())
                if 0 <= gi < len(alive) and 0 <= ri < len(unique_relics):
                    msg = alive[gi].equip(unique_relics[ri])
                    await self.send(session, {"type": "message", "text": msg, "style": "bold magenta"})
                else:
                    await self.send(session, {"type": "error", "text": "Invalid selection."})
            except (ValueError, IndexError):
                await self.send(session, {"type": "error", "text": "Format: <goop#> <relic#>"})
            await self.send_state(session)
            session.save()

    async def handle_challenge(self, session: PlayerSession, target_name: str):
        if target_name not in self.name_to_id:
            await self.send(session, {"type": "error", "text": f"{target_name} is not online."})
            return
        tid = self.name_to_id[target_name]
        if tid == session.player_id:
            await self.send(session, {"type": "error", "text": "You can't fight yourself!"})
            return
        target = self.sessions[tid]
        target.pending_challenge = session.player_id
        await self.send(target, {
            "type": "challenge_incoming",
            "from": session.player_name,
        })
        await self.send(session, {"type": "message",
            "text": f"Challenge sent to {target_name}! Waiting for response...", "style": "yellow"})

    async def handle_challenge_response(self, session: PlayerSession, accept: bool):
        challenger_id = session.pending_challenge
        session.pending_challenge = None
        if not challenger_id or challenger_id not in self.sessions:
            await self.send(session, {"type": "error", "text": "No pending challenge."})
            return
        challenger = self.sessions[challenger_id]

        if not accept:
            await self.send(challenger, {"type": "message",
                "text": f"{session.player_name} declined your challenge.", "style": "yellow"})
            return

        # Run PvP battle
        pair = frozenset([session.player_id, challenger_id])
        if pair in self.pvp_battles:
            await self.send(session, {"type": "error", "text": "Battle already in progress!"})
            return
        self.pvp_battles.add(pair)

        log_lines, winner_id = self._run_pvp(session, challenger)

        for pid in [session.player_id, challenger_id]:
            s = self.sessions[pid]
            await self.send(s, {
                "type": "battle",
                "log": log_lines,
                "won": (pid == winner_id),
            })
            s.save()

        self.pvp_battles.discard(pair)
        # broadcast result
        winner_name = self.sessions[winner_id].player_name if winner_id else "Nobody"
        await self.broadcast({
            "type": "message",
            "text": f"⚔️  PvP: {challenger.player_name} vs {session.player_name} → {winner_name} wins!",
            "style": "bold red",
        })

    def _run_pvp(self, a: PlayerSession, b: PlayerSession) -> tuple[list[str], str]:
        """Simple PvP simulation. Returns (log, winner_player_id)."""
        log: list[str] = [
            f"=== ⚔️  PvP BATTLE ===",
            f"{a.player_name}'s Troop  vs  {b.player_name}'s Troop",
            "",
        ]
        a_power = a.troop.troop_power
        b_power = b.troop.troop_power
        log.append(f"{a.player_name} Power: {a_power}   {b.player_name} Power: {b_power}")
        log.append("")

        a_hp = a_power
        b_hp = b_power
        rounds = 0
        while a_hp > 0 and b_hp > 0 and rounds < 10:
            rounds += 1
            a_dmg = random.randint(max(1, a_power // 4), max(2, a_power // 2))
            b_dmg = random.randint(max(1, b_power // 4), max(2, b_power // 2))
            b_hp -= a_dmg
            a_hp -= b_dmg
            log.append(f"Round {rounds}: {a.player_name} deals {a_dmg}  |  {b.player_name} deals {b_dmg}")

        if a_hp > b_hp:
            winner_id = a.player_id
            log.append(f"\n🏆 {a.player_name}'s troop emerges victorious!")
            a.troop.goop_bucks += 50
            a.troop.reputation += 3
            b.troop.reputation = max(0, b.troop.reputation - 1)
        elif b_hp > a_hp:
            winner_id = b.player_id
            log.append(f"\n🏆 {b.player_name}'s troop emerges victorious!")
            b.troop.goop_bucks += 50
            b.troop.reputation += 3
            a.troop.reputation = max(0, a.troop.reputation - 1)
        else:
            winner_id = random.choice([a.player_id, b.player_id])
            log.append(f"\n🤝 A dramatic tie! {self.sessions[winner_id].player_name} edges it out!")

        return log, winner_id

    # ── Main handler ──────────────────────────────────────────────────────────

    async def handler(self, ws: WebSocketServerProtocol):
        session: PlayerSession | None = None
        try:
            async for raw in ws:
                try:
                    msg: dict[str, Any] = json.loads(raw)
                except json.JSONDecodeError:
                    await ws.send(json.dumps({"type": "error", "text": "Invalid JSON"}))
                    continue

                mtype = msg.get("type", "")

                if mtype == "ping":
                    await ws.send(json.dumps({"type": "pong"}))
                    continue

                if mtype == "join":
                    session = await self.handle_join(ws, msg)
                    continue

                if session is None:
                    await ws.send(json.dumps({"type": "error", "text": "Send 'join' first."}))
                    continue

                if mtype == "action":
                    await self.handle_action(session, msg.get("action", ""))

                elif mtype == "input":
                    await self.handle_input(session, msg.get("value", ""), msg.get("tag", ""))

                elif mtype == "challenge":
                    target = msg.get("target", "")
                    if msg.get("accept") is not None:
                        await self.handle_challenge_response(session, bool(msg["accept"]))
                    else:
                        await self.handle_challenge(session, target)

                else:
                    await self.send(session, {"type": "error", "text": f"Unknown message type: {mtype}"})

        except websockets.exceptions.ConnectionClosed:
            pass
        finally:
            if session:
                session.save()
                del self.sessions[session.player_id]
                self.name_to_id.pop(session.player_name, None)
                await self.broadcast({
                    "type": "message",
                    "text": f"💧 {session.player_name} has dripped offline.",
                    "style": "dim",
                })


# ── Entry point ───────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="GoopGoopDroopTroop multiplayer server")
    parser.add_argument("--host", default="0.0.0.0", help="Bind host (default: 0.0.0.0)")
    parser.add_argument("--port", type=int, default=19500, help="Bind port (default: 19500)")
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(level=level, format="%(asctime)s [%(levelname)s] %(message)s")

    server = GameServer()

    async def run():
        log.info(f"GoopGoopDroopTroop server starting on ws://{args.host}:{args.port}")
        async with websockets.serve(server.handler, args.host, args.port):
            log.info("Server ready. Awaiting goops...")
            await asyncio.Future()

    asyncio.run(run())
