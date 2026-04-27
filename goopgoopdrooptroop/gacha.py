"""Gacha system - banners, pulls, pity, and relics for your goop troop."""

from __future__ import annotations

import random
from dataclasses import dataclass, field, asdict
from typing import Literal

# ── Rarity ──────────────────────────────────────────────────────────────────

Rarity = Literal["common", "rare", "epic", "legendary"]

RARITY_COLORS = {
    "common": "white",
    "rare": "blue",
    "epic": "magenta",
    "legendary": "bold yellow",
}

RARITY_EMOJI = {
    "common": "⚪",
    "rare": "🔵",
    "epic": "🟣",
    "legendary": "🌟",
}

# Base pull-rate percentages (single pull)
BASE_RATES: dict[Rarity, float] = {
    "legendary": 0.006,   # 0.6%
    "epic":      0.051,   # 5.1%
    "rare":      0.243,   # 24.3%
    "common":    0.700,   # 70.0%
}

PITY_LEGENDARY = 90   # guaranteed legendary after this many pulls without one
PITY_EPIC      = 10   # guaranteed epic after this many pulls without one

PULL_COST_SINGLE = 160   # GoopBucks per single pull
PULL_COST_TEN    = 1440  # GoopBucks per 10-pull (10% discount)


# ── Relic (item) ─────────────────────────────────────────────────────────────

@dataclass
class Relic:
    """An equippable item a goop can hold."""
    id: str
    name: str
    description: str
    rarity: Rarity
    # stat bonuses applied when equipped
    attack_bonus:   int = 0
    defense_bonus:  int = 0
    goopiness_bonus: int = 0
    droopiness_penalty: int = 0   # positive = bad for the goop
    morale_bonus:   int = 0
    xp_multiplier:  float = 1.0   # multiplies XP gains

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> Relic:
        return cls(**data)

    def stat_line(self) -> str:
        parts: list[str] = []
        if self.attack_bonus:
            parts.append(f"ATK +{self.attack_bonus}")
        if self.defense_bonus:
            parts.append(f"DEF +{self.defense_bonus}")
        if self.goopiness_bonus:
            parts.append(f"Goop +{self.goopiness_bonus}")
        if self.droopiness_penalty:
            parts.append(f"Droop +{self.droopiness_penalty}")
        if self.morale_bonus:
            parts.append(f"Morale +{self.morale_bonus}")
        if self.xp_multiplier != 1.0:
            parts.append(f"XP x{self.xp_multiplier:.1f}")
        return "  ".join(parts) if parts else "No stat bonuses"


# ── Relic Pool ───────────────────────────────────────────────────────────────

RELIC_POOL: list[Relic] = [
    # ── COMMON ──────────────────────────────────────────────────────────────
    Relic("goop_rag", "Goop Rag", "A worn rag soaked in goop essence.", "common",
          attack_bonus=1, defense_bonus=1),
    Relic("drip_pouch", "Drip Pouch", "Keeps excess goop from dripping.", "common",
          droopiness_penalty=-3, morale_bonus=2),
    Relic("pebble", "Lucky Pebble", "It's just a rock. But it feels lucky.", "common",
          goopiness_bonus=3),
    Relic("goop_boots", "Goop Boots", "Keeps their feet from fusing to the floor.", "common",
          defense_bonus=2),
    Relic("slime_wrap", "Slime Wrap", "Protective slime bandages.", "common",
          defense_bonus=3, droopiness_penalty=1),

    # ── RARE ────────────────────────────────────────────────────────────────
    Relic("bubble_shield", "Bubble Shield", "A shield made of compressed goop bubbles.", "rare",
          defense_bonus=8, goopiness_bonus=5),
    Relic("ooze_blade", "Ooze Blade", "A blade forged from crystallized droop.", "rare",
          attack_bonus=10, droopiness_penalty=5),
    Relic("morale_horn", "Morale Horn", "When blown, goops feel invincible.", "rare",
          morale_bonus=15, attack_bonus=3),
    Relic("goop_flask", "Goop Flask", "A flask of premium aged goop.", "rare",
          goopiness_bonus=12, morale_bonus=8),
    Relic("droop_filter", "Droop Filter", "Filters out excess droopiness.", "rare",
          droopiness_penalty=-10, defense_bonus=4),
    Relic("xp_talisman", "XP Talisman", "Ancient rune that accelerates growth.", "rare",
          xp_multiplier=1.3, goopiness_bonus=5),

    # ── EPIC ────────────────────────────────────────────────────────────────
    Relic("ooze_core", "Ooze Core", "The crystallized heart of an ancient goop entity.", "epic",
          attack_bonus=18, defense_bonus=10, goopiness_bonus=15),
    Relic("droop_crown", "Droop Crown", "Worn by the legendary Droop King. Heavy.", "epic",
          defense_bonus=20, droopiness_penalty=-20, morale_bonus=10),
    Relic("slime_shroud", "Slime Shroud", "A cloak woven from ten thousand goop strands.", "epic",
          attack_bonus=10, defense_bonus=15, goopiness_bonus=20),
    Relic("goop_crystal", "Goop Crystal", "Pulsing with condensed goop energy.", "epic",
          xp_multiplier=1.75, goopiness_bonus=25, morale_bonus=20),
    Relic("battle_slime", "Battle Slime", "An ancient war-goop symbiote.", "epic",
          attack_bonus=25, droopiness_penalty=10, morale_bonus=5),

    # ── LEGENDARY ───────────────────────────────────────────────────────────
    Relic("primordial_goop", "Primordial Goop", "The original goop. From which all goops came.", "legendary",
          attack_bonus=35, defense_bonus=25, goopiness_bonus=40, morale_bonus=30,
          xp_multiplier=2.0),
    Relic("crown_of_infinite_droop", "Crown of Infinite Droop",
          "Those who wear it transcend droopiness itself.", "legendary",
          defense_bonus=50, droopiness_penalty=-50, morale_bonus=40),
    Relic("the_last_splorch", "The Last Splorch",
          "A legendary goop soldier's final gift to the world.", "legendary",
          attack_bonus=45, goopiness_bonus=35, xp_multiplier=2.5),
    Relic("goop_singularity", "Goop Singularity",
          "A point where all goop converges. Terrifying. Perfect.", "legendary",
          attack_bonus=30, defense_bonus=30, goopiness_bonus=50, morale_bonus=50,
          xp_multiplier=3.0, droopiness_penalty=-30),
]

_POOL_BY_RARITY: dict[Rarity, list[Relic]] = {r: [] for r in ("common", "rare", "epic", "legendary")}
for _relic in RELIC_POOL:
    _POOL_BY_RARITY[_relic.rarity].append(_relic)


# ── Banner ───────────────────────────────────────────────────────────────────

@dataclass
class Banner:
    name: str
    description: str
    featured: list[str]   # relic ids with boosted rate when their rarity hits
    featured_boost: float = 0.5  # 50% chance to get featured item vs random pool item

    def pick_featured_or_pool(self, rarity: Rarity) -> Relic:
        pool = _POOL_BY_RARITY[rarity]
        featured_pool = [r for r in pool if r.id in self.featured]
        if featured_pool and random.random() < self.featured_boost:
            return random.choice(featured_pool)
        return random.choice(pool)


BANNERS: list[Banner] = [
    Banner(
        name="Standard - The Goop Armory",
        description="The classic banner. Balanced pulls across all rarities.",
        featured=[],
    ),
    Banner(
        name="Droop Knight's Arsenal",
        description="Featured: Droop Crown, Ooze Blade, Slime Wrap. Boosted defense relics!",
        featured=["droop_crown", "ooze_blade", "slime_wrap", "bubble_shield"],
    ),
    Banner(
        name="Goop Singularity Event",
        description="Featured: Goop Singularity. Boosted XP and offensive relics!",
        featured=["goop_singularity", "xp_talisman", "goop_crystal", "ooze_core"],
    ),
    Banner(
        name="The Primordial Pull",
        description="Featured: Primordial Goop and The Last Splorch. Raw power!",
        featured=["primordial_goop", "the_last_splorch", "battle_slime"],
    ),
]


# ── Gacha State (per-player) ──────────────────────────────────────────────────

@dataclass
class GachaState:
    pulls_since_legendary: int = 0
    pulls_since_epic: int = 0
    total_pulls: int = 0
    inventory: list[dict] = field(default_factory=list)  # list of relic dicts
    active_banner_idx: int = 0

    # ── serialization ────────────────────────────────────────────────────────
    def to_dict(self) -> dict:
        return {
            "pulls_since_legendary": self.pulls_since_legendary,
            "pulls_since_epic": self.pulls_since_epic,
            "total_pulls": self.total_pulls,
            "inventory": self.inventory,
            "active_banner_idx": self.active_banner_idx,
        }

    @classmethod
    def from_dict(cls, data: dict) -> GachaState:
        obj = cls(
            pulls_since_legendary=data.get("pulls_since_legendary", 0),
            pulls_since_epic=data.get("pulls_since_epic", 0),
            total_pulls=data.get("total_pulls", 0),
            active_banner_idx=data.get("active_banner_idx", 0),
        )
        obj.inventory = data.get("inventory", [])
        return obj

    @property
    def active_banner(self) -> Banner:
        return BANNERS[self.active_banner_idx % len(BANNERS)]

    # ── inventory helpers ────────────────────────────────────────────────────
    def get_inventory_relics(self) -> list[Relic]:
        return [Relic.from_dict(d) for d in self.inventory]

    def add_relic(self, relic: Relic):
        self.inventory.append(relic.to_dict())

    def has_relic(self, relic_id: str) -> bool:
        return any(d["id"] == relic_id for d in self.inventory)

    # ── core pull logic ───────────────────────────────────────────────────────
    def _roll_rarity(self) -> Rarity:
        """Roll rarity with pity taken into account."""
        if self.pulls_since_legendary >= PITY_LEGENDARY - 1:
            return "legendary"
        if self.pulls_since_epic >= PITY_EPIC - 1:
            rarity: Rarity = "epic" if random.random() < 0.5 else "legendary"
            return rarity

        # Soft pity: odds boost as you approach pity threshold
        legendary_rate = BASE_RATES["legendary"]
        if self.pulls_since_legendary >= PITY_LEGENDARY * 0.75:
            legendary_rate = BASE_RATES["legendary"] + (
                (self.pulls_since_legendary - PITY_LEGENDARY * 0.75)
                / (PITY_LEGENDARY * 0.25)
            ) * 0.15

        roll = random.random()
        if roll < legendary_rate:
            return "legendary"
        roll -= legendary_rate
        if roll < BASE_RATES["epic"]:
            return "epic"
        roll -= BASE_RATES["epic"]
        if roll < BASE_RATES["rare"]:
            return "rare"
        return "common"

    def _do_pull(self) -> Relic:
        rarity = self._roll_rarity()
        relic = self.active_banner.pick_featured_or_pool(rarity)

        self.total_pulls += 1
        if rarity == "legendary":
            self.pulls_since_legendary = 0
            self.pulls_since_epic = 0
        elif rarity == "epic":
            self.pulls_since_legendary += 1
            self.pulls_since_epic = 0
        else:
            self.pulls_since_legendary += 1
            self.pulls_since_epic += 1

        self.add_relic(relic)
        return relic

    def single_pull(self) -> Relic:
        return self._do_pull()

    def ten_pull(self) -> list[Relic]:
        results: list[Relic] = []
        for _ in range(10):
            results.append(self._do_pull())
        # guaranteed at least one rare in 10-pull
        if not any(r.rarity in ("rare", "epic", "legendary") for r in results):
            # replace the last common with a random rare
            pool = _POOL_BY_RARITY["rare"]
            results[-1] = random.choice(pool)
            # update inventory (last entry)
            self.inventory[-1] = results[-1].to_dict()
        return results

    def pity_info(self) -> str:
        leg_left = PITY_LEGENDARY - self.pulls_since_legendary
        epic_left = PITY_EPIC - self.pulls_since_epic
        return (
            f"Legendary pity: {self.pulls_since_legendary}/{PITY_LEGENDARY} "
            f"(guaranteed in {leg_left})\n"
            f"Epic pity: {self.pulls_since_epic}/{PITY_EPIC} "
            f"(guaranteed in {epic_left})"
        )
