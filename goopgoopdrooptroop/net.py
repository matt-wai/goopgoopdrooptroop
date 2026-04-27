"""Multiplayer client for GoopGoopDroopTroop.

Usage:
    ggdt-mp --host localhost --port 8765 --name YourName
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
import uuid
from pathlib import Path
from typing import Any

import websockets
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich import box

from .art import BANNER
from .gacha import BANNERS, PULL_COST_SINGLE, PULL_COST_TEN, RARITY_EMOJI

console = Console()

CLIENT_ID_FILE = Path.home() / ".goopgoopdrooptroop" / "client_id"


def get_or_create_client_id() -> str:
    CLIENT_ID_FILE.parent.mkdir(parents=True, exist_ok=True)
    if CLIENT_ID_FILE.exists():
        return CLIENT_ID_FILE.read_text().strip()
    cid = str(uuid.uuid4())
    CLIENT_ID_FILE.write_text(cid)
    return cid


def render_state(state: dict):
    troop = state.get("troop", {})
    online = state.get("online", [])

    console.rule("[bold green]Your Troop[/bold green]")
    goops = troop.get("goops", [])
    if goops:
        tbl = Table(box=box.SIMPLE_HEAVY, border_style="green", show_lines=True)
        tbl.add_column("#", style="dim", width=3)
        tbl.add_column("Name", style="bold cyan", min_width=14)
        tbl.add_column("Lvl", justify="center", style="yellow")
        tbl.add_column("HP", justify="center")
        tbl.add_column("ATK", justify="center", style="red")
        tbl.add_column("DEF", justify="center", style="blue")
        tbl.add_column("Goop%", justify="center", style="green")
        tbl.add_column("Droop%", justify="center", style="magenta")
        tbl.add_column("Relic", style="yellow", min_width=16)
        tbl.add_column("Power", justify="center", style="bold yellow")

        for i, g in enumerate(goops):
            alive = g.get("alive", True)
            relic = g.get("equipped_relic")
            relic_name = relic["name"] if relic else "-"
            hp = g.get("hp", 0)
            mhp = g.get("max_hp", 100)
            hp_color = "green" if hp > mhp * 0.5 else "yellow" if hp > mhp * 0.25 else "red"
            tbl.add_row(
                str(i + 1),
                g["name"] if alive else f"[strike]{g['name']}[/strike]",
                str(g.get("level", 1)),
                f"[{hp_color}]{hp}/{mhp}[/{hp_color}]",
                str(g.get("attack", 0)),
                str(g.get("defense", 0)),
                str(g.get("goopiness", 0)),
                str(g.get("droopiness", 0)),
                relic_name,
                str(g.get("power", 0)) if alive else "---",
            )
        console.print(tbl)

    console.print(
        f"  [bold yellow]GoopBucks:[/bold yellow] {troop.get('goop_bucks', 0)}  "
        f"[bold magenta]Rep:[/bold magenta] {troop.get('reputation', 0)}  "
        f"[bold cyan]Missions:[/bold cyan] {troop.get('total_missions', 0)}  "
        f"[bold green]Power:[/bold green] {troop.get('troop_power', 0)}"
    )
    gacha_pity = troop.get("gacha_pity", "")
    banner = troop.get("banner", "?")
    inventory_count = len(troop.get("gacha_inventory", []))
    console.print(
        f"  [bold]Banner:[/bold] {banner}  "
        f"[dim]{gacha_pity}[/dim]  "
        f"[yellow]Relics owned: {inventory_count}[/yellow]"
    )

    if online:
        console.rule("[bold blue]Online Players[/bold blue]")
        tbl2 = Table(box=box.SIMPLE, show_header=True, border_style="blue")
        tbl2.add_column("Player", style="bold cyan")
        tbl2.add_column("Goops", justify="center")
        tbl2.add_column("Power", justify="center", style="yellow")
        tbl2.add_column("Rep", justify="center", style="magenta")
        for p in online:
            tbl2.add_row(p["name"], str(p["goops"]), str(p["power"]), str(p["reputation"]))
        console.print(tbl2)
    console.print()


def show_menu():
    console.print(Panel(
        "[bold cyan]── MISSIONS & TROOP ──[/bold cyan]\n"
        "[m] ⚔️  Run a Mission (auto-squad)\n"
        "[r] 🆕 Recruit a Goop\n"
        "[F] 🍖 Feed all Goops\n"
        "[T] 💪 Train all Goops\n"
        "[R] 😴 Rest all Goops\n"
        "[t] ⏱  Tick (time passes)\n"
        "\n[bold magenta]── GACHA ──[/bold magenta]\n"
        f"[1] 🎰 Single Pull ({PULL_COST_SINGLE} GoopBucks)\n"
        f"[x] 🎰 10-Pull ({PULL_COST_TEN} GoopBucks)\n"
        "[b] 🏳  Switch Banner\n"
        "[i] 📦 View Relic Inventory\n"
        "[e] 💍 Equip Relic to Goop\n"
        "\n[bold red]── MULTIPLAYER ──[/bold red]\n"
        "[c] ⚔️  Challenge a Player\n"
        "[s] 📊 Refresh State\n"
        "[q] 💾 Quit\n",
        title="[bold green]~ GGDT Multiplayer ~[/bold green]",
        border_style="green",
    ))


async def run_client(host: str, port: int, player_name: str):
    url = f"ws://{host}:{port}"
    client_id = get_or_create_client_id()

    console.print(Text(BANNER, style="bold green"))
    console.print(f"[dim]Connecting to {url} as [bold]{player_name}[/bold]...[/dim]")

    pending_tag: str | None = None
    state_cache: dict = {}

    async with websockets.connect(url, ping_interval=20, ping_timeout=10) as ws:

        async def recv_loop():
            nonlocal pending_tag, state_cache
            async for raw in ws:
                msg: dict[str, Any] = json.loads(raw)
                mtype = msg.get("type", "")

                if mtype == "welcome":
                    console.print(f"\n[bold green]Connected as {msg['player_name']}![/bold green]")

                elif mtype == "state":
                    state_cache = msg
                    render_state(msg)

                elif mtype == "message":
                    style = msg.get("style", "")
                    console.print(f"[{style}]{msg['text']}[/{style}]" if style else msg["text"])

                elif mtype == "error":
                    console.print(f"[bold red]Error:[/bold red] {msg['text']}")

                elif mtype == "battle":
                    color = "green" if msg["won"] else "red"
                    console.print(Panel(
                        "\n".join(msg["log"]),
                        title=f"[bold {color}]{'VICTORY' if msg['won'] else 'DEFEAT'}[/bold {color}]",
                        border_style=color,
                    ))

                elif mtype == "prompt":
                    nonlocal pending_tag  # noqa: F821 - set via closure
                    pending_tag = msg.get("tag")
                    console.print(f"\n[bold yellow]{msg['text']}[/bold yellow]")

                elif mtype == "challenge_incoming":
                    frm = msg["from"]
                    console.print(
                        f"\n[bold red]⚔️  CHALLENGE from {frm}! "
                        f"Type 'accept {frm}' or 'decline {frm}'[/bold red]"
                    )

                elif mtype == "pong":
                    pass

        recv_task = asyncio.create_task(recv_loop())

        # Join
        await ws.send(json.dumps({
            "type": "join",
            "player_name": player_name,
            "player_id": client_id,
        }))

        # Input loop
        loop = asyncio.get_event_loop()
        try:
            while True:
                show_menu()
                raw_input = await loop.run_in_executor(
                    None, lambda: console.input("[bold yellow]> [/bold yellow]").strip()
                )

                if not raw_input:
                    continue

                # Handle pending prompt (e.g. banner select, equip)
                if pending_tag:
                    await ws.send(json.dumps({
                        "type": "input",
                        "value": raw_input,
                        "tag": pending_tag,
                    }))
                    pending_tag = None
                    continue

                choice = raw_input.lower()

                if choice in ("q", "quit", "exit"):
                    console.print("[bold green]Farewell, commander. Your goops will droop without you.[/bold green]")
                    break

                elif choice == "s":
                    # just wait for next state push; request a tick to force update
                    await ws.send(json.dumps({"type": "action", "action": "tick"}))

                elif choice == "m":
                    await ws.send(json.dumps({"type": "action", "action": "mission"}))

                elif choice == "r":
                    await ws.send(json.dumps({"type": "action", "action": "recruit"}))

                elif choice == "F":
                    await ws.send(json.dumps({"type": "action", "action": "feed_all"}))

                elif choice == "T":
                    await ws.send(json.dumps({"type": "action", "action": "train_all"}))

                elif choice == "R":
                    await ws.send(json.dumps({"type": "action", "action": "rest_all"}))

                elif choice == "t":
                    await ws.send(json.dumps({"type": "action", "action": "tick"}))

                elif choice == "1":
                    await ws.send(json.dumps({"type": "action", "action": "gacha_single"}))

                elif choice == "x":
                    await ws.send(json.dumps({"type": "action", "action": "gacha_ten"}))

                elif choice == "b":
                    await ws.send(json.dumps({"type": "action", "action": "gacha_switch_banner"}))

                elif choice == "i":
                    await ws.send(json.dumps({"type": "action", "action": "gacha_inventory"}))

                elif choice == "e":
                    await ws.send(json.dumps({"type": "action", "action": "gacha_equip"}))

                elif choice.startswith("c ") or choice == "c":
                    parts = raw_input.split(maxsplit=1)
                    if len(parts) < 2:
                        target = await loop.run_in_executor(
                            None, lambda: console.input("[yellow]Challenge who? > [/yellow]").strip()
                        )
                    else:
                        target = parts[1]
                    await ws.send(json.dumps({"type": "challenge", "target": target}))

                elif raw_input.lower().startswith("accept "):
                    frm = raw_input.split(maxsplit=1)[1]
                    await ws.send(json.dumps({"type": "challenge", "target": frm, "accept": True}))

                elif raw_input.lower().startswith("decline "):
                    frm = raw_input.split(maxsplit=1)[1]
                    await ws.send(json.dumps({"type": "challenge", "target": frm, "accept": False}))

                else:
                    console.print("[red]Unknown command![/red]")

        except (KeyboardInterrupt, EOFError):
            pass
        finally:
            recv_task.cancel()
            try:
                await recv_task
            except asyncio.CancelledError:
                pass


def main():
    parser = argparse.ArgumentParser(description="GoopGoopDroopTroop multiplayer client")
    parser.add_argument("--host", default="localhost", help="Server host (default: localhost)")
    parser.add_argument("--port", type=int, default=19500, help="Server port (default: 19500)")
    parser.add_argument("--name", default="GoopCommander", help="Your player name")
    args = parser.parse_args()

    asyncio.run(run_client(args.host, args.port, args.name))
