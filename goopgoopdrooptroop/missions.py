"""Mission system for the goop troop."""

from __future__ import annotations

import random
import time
from dataclasses import dataclass

from .art import MISSION_FLAVOR, VICTORY_LINES, DEFEAT_LINES
from .goop import Goop, Troop


@dataclass
class Mission:
    name: str
    description: str
    difficulty: int
    reward_bucks: int
    reward_xp: int
    reputation_gain: int

    @classmethod
    def generate(cls, troop_power: int) -> Mission:
        tier = max(1, troop_power // 20)
        names = [
            "The Sludge Pits of Despair",
            "Goblin Goop Retrieval",
            "The Great Slime Heist",
            "Defend the Goop Reservoir",
            "Infiltrate the Anti-Goop League",
            "The Droop Dragon's Lair",
            "Escort the Goop Caravan",
            "The Ooze Olympics",
            "Reclaim the Lost Puddle",
            "Operation: Maximum Goop",
            "The Blob Baron's Fortress",
            "Slime Summit Peace Treaty",
            "The Goop Gauntlet",
            "Search for the Golden Gloop",
            "The Haunted Swamp Expedition",
        ]
        difficulty = random.randint(max(1, tier - 2), tier + 3)
        return cls(
            name=random.choice(names),
            description=random.choice(MISSION_FLAVOR),
            difficulty=difficulty,
            reward_bucks=difficulty * random.randint(10, 25),
            reward_xp=difficulty * random.randint(5, 15),
            reputation_gain=random.randint(1, difficulty),
        )


def run_mission(troop: Troop, squad: list[Goop], mission: Mission) -> tuple[bool, list[str]]:
    """Execute a mission with the selected squad. Returns (won, log_lines)."""
    log: list[str] = []
    log.append(f"=== MISSION: {mission.name} ===")
    log.append(f"Difficulty: {'💀' * mission.difficulty}")
    log.append(f"")
    log.append(mission.description)
    log.append("")

    squad_power = sum(g.power for g in squad if g.alive)
    enemy_power = mission.difficulty * random.randint(8, 15)

    log.append(f"Squad Power: {squad_power}  vs  Enemy Power: {enemy_power}")
    log.append("")

    rounds = random.randint(2, 5)
    for r in range(1, rounds + 1):
        log.append(f"--- Round {r} ---")

        for goop in squad:
            if not goop.alive:
                continue
            dmg_dealt = random.randint(goop.attack // 2, goop.attack + goop.goopiness // 5)
            enemy_power -= dmg_dealt
            log.append(f"  {goop.name} deals {dmg_dealt} goop damage!")

            if random.random() < 0.4:
                enemy_dmg = random.randint(mission.difficulty * 2, mission.difficulty * 5)
                result = goop.take_damage(enemy_dmg)
                log.append(f"  {result}")

        if enemy_power <= 0:
            log.append("")
            log.append(random.choice(VICTORY_LINES))
            break

    won = enemy_power <= 0

    if won:
        troop.goop_bucks += mission.reward_bucks
        troop.reputation += mission.reputation_gain
        troop.total_missions += 1
        log.append(f"  +{mission.reward_bucks} GoopBucks!")
        log.append(f"  +{mission.reputation_gain} Reputation!")
        for g in squad:
            if g.alive:
                g.xp += int(mission.reward_xp * g.xp_multiplier)
                g.missions_completed += 1
                g.morale = min(100, g.morale + random.randint(5, 15))
                levelup = g._check_levelup()
                if levelup:
                    log.append(f"  🎉 {levelup}")
    else:
        log.append("")
        log.append(random.choice(DEFEAT_LINES))
        troop.reputation = max(0, troop.reputation - 1)
        for g in squad:
            if g.alive:
                g.morale = max(0, g.morale - random.randint(10, 25))
                g.droopiness = min(100, g.droopiness + random.randint(5, 15))

    return won, log
