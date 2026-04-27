"""Goop soldier class and troop management."""

from __future__ import annotations

import json
import random
import time
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Optional, TYPE_CHECKING

from .art import random_goop_name

if TYPE_CHECKING:
    from .gacha import Relic, GachaState

SAVE_DIR = Path.home() / ".goopgoopdrooptroop"
SAVE_FILE = SAVE_DIR / "troop.json"


@dataclass
class Goop:
    name: str
    level: int = 1
    xp: int = 0
    hp: int = 100
    max_hp: int = 100
    attack: int = 10
    defense: int = 5
    goopiness: int = 50  # 0-100 how goop are they
    droopiness: int = 20  # 0-100 how droop are they
    hunger: int = 50  # 0-100
    morale: int = 70  # 0-100
    alive: bool = True
    missions_completed: int = 0
    kills: int = 0
    created_at: float = field(default_factory=time.time)
    equipped_relic: Optional[dict] = None  # serialized Relic dict or None

    @property
    def mood(self) -> str:
        if not self.alive:
            return "dead"
        if self.morale > 90:
            return "ecstatic"
        if self.morale > 65:
            return "happy"
        if self.morale > 40:
            return "content"
        if self.morale > 20:
            return "droopy"
        return "miserable"

    @property
    def relic(self) -> Optional["Relic"]:
        if self.equipped_relic is None:
            return None
        from .gacha import Relic as _Relic
        return _Relic.from_dict(self.equipped_relic)

    def equip(self, relic: "Relic") -> str:
        old = self.relic
        self.equipped_relic = relic.to_dict()
        if old:
            return f"{self.name} swapped [{old.name}] for [{relic.name}]!"
        return f"{self.name} equipped [{relic.name}]!"

    def unequip(self) -> str:
        if not self.equipped_relic:
            return f"{self.name} has nothing equipped."
        name = self.equipped_relic["name"]
        self.equipped_relic = None
        return f"{self.name} unequipped [{name}]."

    @property
    def power(self) -> int:
        r = self.relic
        atk = self.attack + (r.attack_bonus if r else 0)
        def_ = self.defense + (r.defense_bonus if r else 0)
        goop = self.goopiness + (r.goopiness_bonus if r else 0)
        droop = self.droopiness + (r.droopiness_penalty if r else 0)
        morale = min(100, self.morale + (r.morale_bonus if r else 0))
        base = atk + def_ + self.level * 3
        goop_bonus = goop // 10
        droop_penalty = max(0, droop) // 20
        morale_factor = max(0.5, morale / 100)
        return int((base + goop_bonus - droop_penalty) * morale_factor)

    @property
    def xp_multiplier(self) -> float:
        r = self.relic
        return r.xp_multiplier if r else 1.0

    def feed(self) -> str:
        if not self.alive:
            return f"{self.name} is... no longer with us. Feeding won't help."
        amount = random.randint(15, 35)
        self.hunger = max(0, self.hunger - amount)
        self.morale = min(100, self.morale + random.randint(3, 10))
        self.goopiness = min(100, self.goopiness + random.randint(1, 5))
        flavors = [
            f"{self.name} slurps up the goop chow happily!",
            f"{self.name} absorbs nutrients through osmosis. Efficient!",
            f"{self.name} eats so fast some goop flies off. Gross!",
            f"{self.name} savors each bite. Sophistigoop.",
        ]
        return random.choice(flavors)

    def train(self) -> str:
        if not self.alive:
            return f"{self.name} has ascended to the great goop puddle in the sky."
        self.hunger = min(100, self.hunger + random.randint(5, 15))
        stat = random.choice(["attack", "defense", "goopiness"])
        gain = random.randint(1, 3 + self.level)
        setattr(self, stat, getattr(self, stat) + gain)
        raw_xp = random.randint(5, 15)
        self.xp += int(raw_xp * self.xp_multiplier)
        self._check_levelup()
        flavors = [
            f"{self.name} trains {stat}! +{gain}! The goop is strong with this one.",
            f"{self.name} does 100 goop-ups and gains +{gain} {stat}!",
            f"{self.name} studies the ancient art of goop-fu. +{gain} {stat}!",
        ]
        return random.choice(flavors)

    def rest(self) -> str:
        if not self.alive:
            return f"{self.name} rests... eternally."
        heal = random.randint(10, 30)
        self.hp = min(self.max_hp, self.hp + heal)
        self.droopiness = max(0, self.droopiness - random.randint(5, 15))
        self.morale = min(100, self.morale + random.randint(2, 8))
        return f"{self.name} rests and recovers {heal} HP. The droop fades."

    def _check_levelup(self) -> Optional[str]:
        needed = self.level * 25
        if self.xp >= needed:
            self.xp -= needed
            self.level += 1
            self.max_hp += random.randint(5, 15)
            self.hp = self.max_hp
            self.attack += random.randint(1, 3)
            self.defense += random.randint(1, 2)
            return f"{self.name} LEVELED UP to {self.level}!"
        return None

    def take_damage(self, dmg: int) -> str:
        actual = max(1, dmg - self.defense // 3)
        self.hp -= actual
        if self.hp <= 0:
            self.hp = 0
            self.alive = False
            return f"{self.name} took {actual} damage and has been reduced to a sad puddle..."
        return f"{self.name} took {actual} damage! ({self.hp}/{self.max_hp} HP)"

    def tick(self):
        """Simulate time passing."""
        if not self.alive:
            return
        self.hunger = min(100, self.hunger + random.randint(1, 5))
        if self.hunger > 80:
            self.morale = max(0, self.morale - random.randint(2, 5))
            self.droopiness = min(100, self.droopiness + random.randint(1, 3))
        if self.hunger > 95:
            self.hp = max(1, self.hp - random.randint(1, 5))

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> Goop:
        # forward-compat: ignore unknown keys
        known = {f.name for f in cls.__dataclass_fields__.values()}  # type: ignore[attr-defined]
        return cls(**{k: v for k, v in data.items() if k in known})


@dataclass
class Troop:
    goops: list[Goop] = field(default_factory=list)
    goop_bucks: int = 100
    total_missions: int = 0
    reputation: int = 0
    gacha: "GachaState | None" = field(default=None, repr=False)

    def recruit(self, name: str | None = None) -> Goop:
        name = name or random_goop_name()
        cost = 20 + len(self.goops) * 10
        if self.goop_bucks < cost:
            raise ValueError(f"Need {cost} GoopBucks to recruit! You have {self.goop_bucks}.")
        self.goop_bucks -= cost
        goop = Goop(
            name=name,
            attack=random.randint(8, 15),
            defense=random.randint(3, 10),
            goopiness=random.randint(30, 80),
            droopiness=random.randint(10, 40),
        )
        self.goops.append(goop)
        return goop

    @property
    def alive_goops(self) -> list[Goop]:
        return [g for g in self.goops if g.alive]

    @property
    def troop_power(self) -> int:
        return sum(g.power for g in self.alive_goops)

    def tick_all(self):
        for g in self.alive_goops:
            g.tick()

    def get_gacha(self) -> "GachaState":
        if self.gacha is None:
            from .gacha import GachaState
            self.gacha = GachaState()
        return self.gacha

    def save(self):
        SAVE_DIR.mkdir(parents=True, exist_ok=True)
        data: dict = {
            "goop_bucks": self.goop_bucks,
            "total_missions": self.total_missions,
            "reputation": self.reputation,
            "goops": [g.to_dict() for g in self.goops],
        }
        if self.gacha is not None:
            data["gacha"] = self.gacha.to_dict()
        SAVE_FILE.write_text(json.dumps(data, indent=2))

    @classmethod
    def load(cls) -> Troop:
        if not SAVE_FILE.exists():
            return cls()
        data = json.loads(SAVE_FILE.read_text())
        from .gacha import GachaState
        troop = cls(
            goop_bucks=data["goop_bucks"],
            total_missions=data["total_missions"],
            reputation=data["reputation"],
            gacha=GachaState.from_dict(data["gacha"]) if "gacha" in data else GachaState(),
        )
        troop.goops = [Goop.from_dict(g) for g in data["goops"]]
        return troop
