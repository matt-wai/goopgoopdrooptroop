"""Main game loop for GoopGoopDroopTroop."""

from __future__ import annotations

import random
import sys

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.columns import Columns
from rich import box

from .art import BANNER, get_art, IDLE_LINES
from .goop import Goop, Troop
from .missions import Mission, run_mission
from .gacha import (
    BANNERS, PULL_COST_SINGLE, PULL_COST_TEN,
    RARITY_EMOJI, RARITY_COLORS, GachaState,
)

console = Console()


def show_banner():
    console.print(Text(BANNER, style="bold green"))
    console.print(
        Panel(
            "[bold cyan]Command your goop soldiers. Send them on missions.\n"
            "Feed them. Train them. Watch them droop.[/bold cyan]\n\n"
            "[dim]Type a number to select an option. Type 'q' to quit.[/dim]",
            title="[bold yellow]~ Welcome to GoopGoopDroopTroop ~[/bold yellow]",
            border_style="green",
        )
    )


def show_troop_overview(troop: Troop):
    table = Table(
        title="🫠 Your Goop Troop",
        box=box.DOUBLE_EDGE,
        border_style="green",
        show_lines=True,
    )
    table.add_column("#", style="dim", width=3)
    table.add_column("Name", style="bold cyan", min_width=15)
    table.add_column("Lvl", justify="center", style="yellow")
    table.add_column("HP", justify="center")
    table.add_column("ATK", justify="center", style="red")
    table.add_column("DEF", justify="center", style="blue")
    table.add_column("Goop%", justify="center", style="green")
    table.add_column("Droop%", justify="center", style="magenta")
    table.add_column("Relic", style="yellow", min_width=14)
    table.add_column("Mood", justify="center")
    table.add_column("Power", justify="center", style="bold yellow")

    for i, g in enumerate(troop.goops):
        mood = g.mood
        mood_emoji = {
            "ecstatic": "🤩", "happy": "😊", "content": "😐",
            "droopy": "😢", "miserable": "😭", "dead": "💀",
        }.get(mood, "❓")

        hp_color = "green" if g.hp > g.max_hp * 0.5 else "yellow" if g.hp > g.max_hp * 0.25 else "red"
        relic = g.relic
        relic_str = f"{RARITY_EMOJI[relic.rarity]} {relic.name}" if relic else "-"

        table.add_row(
            str(i + 1),
            g.name if g.alive else f"[strike]{g.name}[/strike]",
            str(g.level),
            f"[{hp_color}]{g.hp}/{g.max_hp}[/{hp_color}]",
            str(g.attack),
            str(g.defense),
            str(g.goopiness),
            str(g.droopiness),
            relic_str,
            f"{mood_emoji} {mood}",
            str(g.power) if g.alive else "---",
        )

    console.print(table)
    console.print(
        f"  [bold yellow]GoopBucks:[/bold yellow] {troop.goop_bucks}  "
        f"[bold magenta]Reputation:[/bold magenta] {troop.reputation}  "
        f"[bold cyan]Missions:[/bold cyan] {troop.total_missions}  "
        f"[bold green]Troop Power:[/bold green] {troop.troop_power}"
    )
    console.print()


def show_goop_detail(goop: Goop):
    art = get_art(goop.mood)
    relic = goop.relic
    relic_str = (
        f"{RARITY_EMOJI[relic.rarity]} {relic.name} ({relic.rarity})\n  {relic.stat_line()}"
        if relic else "None"
    )
    info = (
        f"[bold cyan]{goop.name}[/bold cyan] "
        f"(Lvl {goop.level}, XP: {goop.xp}/{goop.level * 25})\n\n"
        f"HP: {goop.hp}/{goop.max_hp}  ATK: {goop.attack}  DEF: {goop.defense}\n"
        f"Goopiness: {goop.goopiness}  Droopiness: {goop.droopiness}\n"
        f"Hunger: {goop.hunger}/100  Morale: {goop.morale}/100\n"
        f"Mood: {goop.mood}  Power: {goop.power}\n"
        f"XP Multiplier: x{goop.xp_multiplier:.1f}\n"
        f"Missions: {goop.missions_completed}  Kills: {goop.kills}\n"
        f"Status: {'🟢 Alive' if goop.alive else '💀 Deceased'}\n\n"
        f"[bold yellow]Equipped Relic:[/bold yellow] {relic_str}"
    )
    panels = [
        Panel(art, title="Portrait", border_style="green", width=30),
        Panel(info, title="Stats", border_style="cyan", width=50),
    ]
    console.print(Columns(panels))


def select_squad(troop: Troop) -> list[Goop] | None:
    alive = troop.alive_goops
    if not alive:
        console.print("[red]No living goops to send on a mission![/red]")
        return None

    console.print("[bold]Select goops for the mission (comma-separated numbers, or 'all'):[/bold]")
    for i, g in enumerate(alive):
        console.print(f"  [{i + 1}] {g.name} (Lvl {g.level}, Power {g.power})")

    choice = console.input("[bold yellow]Squad> [/bold yellow]").strip().lower()
    if choice == "all":
        return alive
    if choice in ("q", "back", "b"):
        return None

    try:
        indices = [int(x.strip()) - 1 for x in choice.split(",")]
        squad = [alive[i] for i in indices if 0 <= i < len(alive)]
        if not squad:
            console.print("[red]No valid goops selected![/red]")
            return None
        return squad
    except (ValueError, IndexError):
        console.print("[red]Invalid selection![/red]")
        return None


def main_menu(troop: Troop) -> str:
    gacha = troop.get_gacha()
    leg_left = 90 - gacha.pulls_since_legendary
    epic_left = 10 - gacha.pulls_since_epic
    console.print(Panel(
        "[bold cyan]── TROOP ──[/bold cyan]\n"
        "[1] 📋 View Troop\n"
        "[2] 🫠 Inspect a Goop\n"
        "[3] 🍖 Feed a Goop\n"
        "[4] 💪 Train a Goop\n"
        "[5] 😴 Rest a Goop\n"
        "[6] ⚔️  Go on a Mission\n"
        "[7] 🆕 Recruit a Goop\n"
        "[8] 🎲 Random Event\n"
        "\n[bold magenta]── GACHA ──[/bold magenta]\n"
        f"[g] 🎰 Gacha Pull Menu  "
        f"[dim](Banner: {gacha.active_banner.name[:25]}... | "
        f"Leg pity: {gacha.pulls_since_legendary}/90 | "
        f"Epic pity: {gacha.pulls_since_epic}/10)[/dim]\n"
        "[r] 💍 Equip Relic to Goop\n"
        "\n[9] 💾 Save & Quit",
        title="[bold green]~ Command Center ~[/bold green]",
        border_style="green",
    ))
    return console.input("[bold yellow]Command> [/bold yellow]").strip()


def pick_goop(troop: Troop, action: str) -> Goop | None:
    alive = troop.alive_goops
    if not alive:
        console.print("[red]No living goops![/red]")
        return None
    console.print(f"[bold]Select a goop to {action}:[/bold]")
    for i, g in enumerate(alive):
        console.print(f"  [{i + 1}] {g.name}")
    choice = console.input("[bold yellow]Goop #> [/bold yellow]").strip()
    try:
        idx = int(choice) - 1
        if 0 <= idx < len(alive):
            return alive[idx]
    except ValueError:
        pass
    console.print("[red]Invalid choice![/red]")
    return None


def random_event(troop: Troop):
    events = [
        ("goop_rain", "☔ A goop rain falls! All goops gain goopiness!"),
        ("tax", "💰 The Goop Tax Collector arrives! -15 GoopBucks."),
        ("gift", "🎁 A mysterious blob leaves a gift! +30 GoopBucks!"),
        ("droop_wave", "😢 A droop wave hits! All goops get droopier."),
        ("morale_boost", "🎉 A traveling goop bard sings! Morale boost!"),
        ("wild_goop", "🫠 A wild goop appears and wants to join!"),
        ("earthquake", "🌋 A slime quake! Some goops take damage!"),
        ("feast", "🍖 You find a cache of goop food! Hunger reduced!"),
    ]
    event_id, message = random.choice(events)
    console.print(Panel(message, title="[bold magenta]~ Random Event ~[/bold magenta]", border_style="magenta"))

    if event_id == "goop_rain":
        for g in troop.alive_goops:
            g.goopiness = min(100, g.goopiness + random.randint(3, 10))
    elif event_id == "tax":
        troop.goop_bucks = max(0, troop.goop_bucks - 15)
    elif event_id == "gift":
        troop.goop_bucks += 30
    elif event_id == "droop_wave":
        for g in troop.alive_goops:
            g.droopiness = min(100, g.droopiness + random.randint(5, 15))
            g.morale = max(0, g.morale - random.randint(3, 8))
    elif event_id == "morale_boost":
        for g in troop.alive_goops:
            g.morale = min(100, g.morale + random.randint(10, 20))
    elif event_id == "wild_goop":
        if len(troop.goops) < 10:
            wild = Goop(
                name=f"Wild {random.choice(['Splorp', 'Gloob', 'Drizzbert', 'Oozwald'])}",
                level=random.randint(1, 3),
                attack=random.randint(8, 18),
                defense=random.randint(3, 12),
                goopiness=random.randint(50, 90),
            )
            troop.goops.append(wild)
            console.print(f"  [green]{wild.name} joined your troop![/green]")
        else:
            console.print("  [yellow]Your troop is full! The wild goop wanders off sadly.[/yellow]")
    elif event_id == "earthquake":
        for g in troop.alive_goops:
            if random.random() < 0.5:
                dmg = random.randint(5, 15)
                g.take_damage(dmg)
    elif event_id == "feast":
        for g in troop.alive_goops:
            g.hunger = max(0, g.hunger - random.randint(15, 30))


def show_gacha_menu(troop: Troop):
    gacha = troop.get_gacha()
    while True:
        console.print(Panel(
            f"[bold]Active Banner:[/bold] {gacha.active_banner.name}\n"
            f"[dim]{gacha.active_banner.description}[/dim]\n\n"
            f"{gacha.pity_info()}\n\n"
            f"[bold yellow]GoopBucks:[/bold yellow] {troop.goop_bucks}\n\n"
            f"[1] 🎰 Single Pull  ({PULL_COST_SINGLE} GB)\n"
            f"[2] 🎰 10-Pull       ({PULL_COST_TEN} GB)  [dim]guaranteed ≥1 rare[/dim]\n"
            f"[3] 📦 View Inventory\n"
            f"[4] 🏳  Switch Banner\n"
            f"[b] ← Back",
            title="[bold magenta]~ Gacha Shop ~[/bold magenta]",
            border_style="magenta",
        ))
        choice = console.input("[bold magenta]Gacha> [/bold magenta]").strip().lower()

        if choice in ("b", "back", "q"):
            break

        elif choice == "1":
            if troop.goop_bucks < PULL_COST_SINGLE:
                console.print(f"[red]Need {PULL_COST_SINGLE} GoopBucks![/red]")
                continue
            troop.goop_bucks -= PULL_COST_SINGLE
            relic = gacha.single_pull()
            console.print(Panel(
                f"{RARITY_EMOJI[relic.rarity]}  [bold {RARITY_COLORS[relic.rarity]}]{relic.name}[/bold {RARITY_COLORS[relic.rarity]}]\n"
                f"[dim]{relic.description}[/dim]\n\n"
                f"{relic.stat_line()}\n\n"
                f"[dim]{gacha.pity_info()}[/dim]",
                title=f"[bold {RARITY_COLORS[relic.rarity]}]~ {relic.rarity.upper()} PULL ~[/bold {RARITY_COLORS[relic.rarity]}]",
                border_style=RARITY_COLORS[relic.rarity].replace("bold ", ""),
            ))

        elif choice == "2":
            if troop.goop_bucks < PULL_COST_TEN:
                console.print(f"[red]Need {PULL_COST_TEN} GoopBucks![/red]")
                continue
            troop.goop_bucks -= PULL_COST_TEN
            relics = gacha.ten_pull()
            lines = [f"  {RARITY_EMOJI[r.rarity]} [{r.rarity.upper():^9}] {r.name}" for r in relics]
            console.print(Panel(
                "\n".join(lines) + f"\n\n[dim]{gacha.pity_info()}[/dim]",
                title="[bold magenta]~ 10-PULL RESULTS ~[/bold magenta]",
                border_style="magenta",
            ))

        elif choice == "3":
            relics = gacha.get_inventory_relics()
            if not relics:
                console.print("[yellow]No relics yet! Start pulling![/yellow]")
                continue
            from collections import Counter
            counts: Counter[str] = Counter(r.id for r in relics)
            tbl = Table(title="📦 Relic Inventory", box=box.SIMPLE_HEAVY, border_style="yellow")
            tbl.add_column("#", style="dim", width=3)
            tbl.add_column("Relic", style="bold", min_width=26)
            tbl.add_column("Rarity", justify="center")
            tbl.add_column("Qty", justify="center")
            tbl.add_column("Stats")
            seen: set[str] = set()
            idx = 1
            for r in relics:
                if r.id not in seen:
                    seen.add(r.id)
                    tbl.add_row(
                        str(idx),
                        f"{RARITY_EMOJI[r.rarity]} {r.name}",
                        f"[{RARITY_COLORS[r.rarity]}]{r.rarity}[/{RARITY_COLORS[r.rarity]}]",
                        str(counts[r.id]),
                        r.stat_line(),
                    )
                    idx += 1
            console.print(tbl)

        elif choice == "4":
            for i, b in enumerate(BANNERS):
                console.print(f"  [{i}] [bold]{b.name}[/bold] - {b.description}")
            raw = console.input("[magenta]Banner #> [/magenta]").strip()
            try:
                gacha.active_banner_idx = int(raw) % len(BANNERS)
                console.print(f"[cyan]Switched to: {gacha.active_banner.name}[/cyan]")
            except ValueError:
                console.print("[red]Invalid input.[/red]")

        else:
            console.print("[red]Unknown option.[/red]")

    troop.save()


def show_equip_menu(troop: Troop):
    gacha = troop.get_gacha()
    relics = gacha.get_inventory_relics()
    alive = troop.alive_goops

    if not relics:
        console.print("[yellow]No relics in inventory. Go pull![/yellow]")
        return
    if not alive:
        console.print("[red]No living goops to equip![/red]")
        return

    # Show goops
    console.print("[bold]Select a Goop:[/bold]")
    for i, g in enumerate(alive):
        relic_name = g.equipped_relic["name"] if g.equipped_relic else "none"
        console.print(f"  [{i + 1}] {g.name} (Power {g.power})  Equipped: {relic_name}")
    gi_raw = console.input("[yellow]Goop #> [/yellow]").strip()
    try:
        gi = int(gi_raw) - 1
        if not (0 <= gi < len(alive)):
            raise ValueError
    except ValueError:
        console.print("[red]Invalid goop selection.[/red]")
        return

    goop = alive[gi]

    # Show unique relics
    from collections import Counter
    counts: Counter[str] = Counter(r.id for r in relics)
    unique: list = []
    seen: set[str] = set()
    for r in relics:
        if r.id not in seen:
            seen.add(r.id)
            unique.append(r)

    console.print("[bold]Select a Relic:[/bold]")
    for i, r in enumerate(unique):
        console.print(
            f"  [{i + 1}] {RARITY_EMOJI[r.rarity]} {r.name} x{counts[r.id]}  |  {r.stat_line()}"
        )
    ri_raw = console.input("[yellow]Relic #> [/yellow]").strip()
    try:
        ri = int(ri_raw) - 1
        if not (0 <= ri < len(unique)):
            raise ValueError
    except ValueError:
        console.print("[red]Invalid relic selection.[/red]")
        return

    msg = goop.equip(unique[ri])
    console.print(f"[bold magenta]{msg}[/bold magenta]")
    troop.save()


def run_game():
    show_banner()
    troop = Troop.load()

    if not troop.goops:
        console.print("\n[bold yellow]Your troop is empty! Let's recruit your first goop![/bold yellow]")
        name = console.input("[bold cyan]Name your first goop (or press Enter for random): [/bold cyan]").strip()
        goop = troop.recruit(name if name else None)
        console.print(f"\n[bold green]Welcome, {goop.name}![/bold green]")
        show_goop_detail(goop)
        troop.save()

    while True:
        console.print()
        idle = random.choice(IDLE_LINES)
        console.print(f"[dim italic]{idle}[/dim italic]\n")

        troop.tick_all()
        choice = main_menu(troop)

        if choice == "1":
            show_troop_overview(troop)

        elif choice == "2":
            goop = pick_goop(troop, "inspect")
            if goop:
                show_goop_detail(goop)

        elif choice == "3":
            goop = pick_goop(troop, "feed")
            if goop:
                result = goop.feed()
                console.print(f"[green]{result}[/green]")

        elif choice == "4":
            goop = pick_goop(troop, "train")
            if goop:
                result = goop.train()
                console.print(f"[cyan]{result}[/cyan]")

        elif choice == "5":
            goop = pick_goop(troop, "rest")
            if goop:
                result = goop.rest()
                console.print(f"[blue]{result}[/blue]")

        elif choice == "6":
            if not troop.alive_goops:
                console.print("[red]No living goops! Recruit or revive first.[/red]")
                continue
            mission = Mission.generate(troop.troop_power)
            console.print(Panel(
                f"[bold]{mission.name}[/bold]\n\n"
                f"{mission.description}\n\n"
                f"Difficulty: {'💀' * mission.difficulty}\n"
                f"Reward: {mission.reward_bucks} GoopBucks, {mission.reward_xp} XP\n"
                f"Reputation: +{mission.reputation_gain}",
                title="[bold red]~ Mission Available ~[/bold red]",
                border_style="red",
            ))
            accept = console.input("[bold]Accept mission? (y/n): [/bold]").strip().lower()
            if accept in ("y", "yes"):
                squad = select_squad(troop)
                if squad:
                    won, log = run_mission(troop, squad, mission)
                    color = "green" if won else "red"
                    console.print(Panel(
                        "\n".join(log),
                        title=f"[bold {color}]~ Mission Report ~[/bold {color}]",
                        border_style=color,
                    ))

        elif choice == "7":
            cost = 20 + len(troop.goops) * 10
            console.print(f"[yellow]Recruitment costs {cost} GoopBucks. You have {troop.goop_bucks}.[/yellow]")
            if troop.goop_bucks >= cost:
                name = console.input("[bold cyan]Name (Enter for random): [/bold cyan]").strip()
                try:
                    goop = troop.recruit(name if name else None)
                    console.print(f"\n[bold green]{goop.name} has joined the troop![/bold green]")
                    show_goop_detail(goop)
                except ValueError as e:
                    console.print(f"[red]{e}[/red]")
            else:
                console.print("[red]Not enough GoopBucks![/red]")

        elif choice == "8":
            random_event(troop)

        elif choice in ("g", "gacha"):
            show_gacha_menu(troop)

        elif choice in ("r", "equip"):
            show_equip_menu(troop)

        elif choice in ("9", "q", "quit", "exit"):
            troop.save()
            console.print("[bold green]Troop saved! Your goops will wait for you... droopily.[/bold green]")
            console.print("[dim]Goodbye, Commander. 🫡[/dim]")
            break

        else:
            console.print("[red]Unknown command! Try a number 1-9.[/red]")

        troop.save()
