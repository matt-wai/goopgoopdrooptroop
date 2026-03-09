"""Web game adapter - state machine for browser-based GoopGoopDroopTroop."""

from __future__ import annotations
import random

from art import BANNER, IDLE_LINES, get_art
from goop import Goop, Troop
from missions import Mission, run_mission

RST = '\033[0m'
BOLD = '\033[1m'
DIM = '\033[2m'
RED = '\033[31m'
GRN = '\033[32m'
YLW = '\033[33m'
BLU = '\033[34m'
MAG = '\033[35m'
CYN = '\033[36m'


def c(text, color):
    return f'{color}{text}{RST}'


def hr(color=GRN, width=60):
    return c('─' * width, color)


def panel(content, title='', color=GRN):
    lines = []
    if title:
        lines.append(c(f'═══ {BOLD}{title}{RST}{color} {"═" * max(1, 53 - len(title))}', color))
    else:
        lines.append(c('═' * 60, color))
    lines.append(content)
    lines.append(c('═' * 60, color))
    return '\n'.join(lines)


MENU_TEXT = f"""{c('[1]', CYN)} View Troop
{c('[2]', CYN)} Inspect a Goop
{c('[3]', CYN)} Feed a Goop
{c('[4]', CYN)} Train a Goop
{c('[5]', CYN)} Rest a Goop
{c('[6]', CYN)} Go on a Mission
{c('[7]', CYN)} Recruit a Goop
{c('[8]', CYN)} Random Event
{c('[9]', CYN)} Save (auto-saves to browser)"""


def format_troop_table(troop: Troop) -> str:
    lines = []
    lines.append(c(BOLD + '  Your Goop Troop', GRN))
    lines.append(hr(GRN))
    header = f"{'#':>2}  {'Name':<16} {'Lvl':>3} {'HP':>9} {'ATK':>4} {'DEF':>4} {'Goop%':>5} {'Mood':<10} {'Pwr':>4}"
    lines.append(c(header, DIM))
    lines.append(hr(DIM, 60))

    for i, g in enumerate(troop.goops):
        mood_icon = {
            "ecstatic": "*_*", "happy": "^_^", "content": "-_-",
            "droopy": "T_T", "miserable": ";_;", "dead": "x_x",
        }.get(g.mood, "?_?")

        hp_col = GRN if g.hp > g.max_hp * 0.5 else YLW if g.hp > g.max_hp * 0.25 else RED
        name_str = g.name if g.alive else f'{DIM}{g.name}{RST}'
        hp_str = c(f'{g.hp:>3}/{g.max_hp:<3}', hp_col)

        row = f"{i+1:>2}  {name_str:<16} {g.level:>3} {hp_str} {g.attack:>4} {g.defense:>4} {g.goopiness:>5} {mood_icon:<10} {g.power if g.alive else '---':>4}"
        lines.append(row)

    lines.append(hr(GRN))
    lines.append(
        f"  {c('GoopBucks:', YLW)} {troop.goop_bucks}  "
        f"{c('Rep:', MAG)} {troop.reputation}  "
        f"{c('Missions:', CYN)} {troop.total_missions}  "
        f"{c('Power:', GRN)} {troop.troop_power}"
    )
    return '\n'.join(lines)


def format_goop_detail(g: Goop) -> str:
    art = get_art(g.mood)
    lines = []
    lines.append(c(f'{BOLD}{g.name}', CYN) + f'  (Lvl {g.level}, XP: {g.xp}/{g.level * 25})')
    lines.append(art)
    lines.append(f"  HP: {g.hp}/{g.max_hp}  ATK: {g.attack}  DEF: {g.defense}")
    lines.append(f"  Goopiness: {g.goopiness}  Droopiness: {g.droopiness}")
    lines.append(f"  Hunger: {g.hunger}/100  Morale: {g.morale}/100")
    lines.append(f"  Mood: {g.mood}  Power: {g.power}")
    lines.append(f"  Missions: {g.missions_completed}  Status: {'Alive' if g.alive else 'Deceased'}")
    return '\n'.join(lines)


def goop_list(troop: Troop) -> str:
    alive = troop.alive_goops
    lines = []
    for i, g in enumerate(alive):
        lines.append(f"  {c(f'[{i+1}]', CYN)} {g.name} (Lvl {g.level}, Pwr {g.power})")
    return '\n'.join(lines)


class WebGame:
    def __init__(self):
        self.troop = Troop.load()
        self.state = 'init'
        self.pending_action = None
        self.pending_mission = None

    def start(self):
        """Returns (output, prompt)."""
        out = c(BANNER, GRN)
        out += '\n' + panel(
            c('Command your goop soldiers. Send them on missions.\n', CYN)
            + c('Feed them. Train them. Watch them droop.', CYN),
            'Welcome to GoopGoopDroopTroop', GRN
        )

        if not self.troop.goops:
            self.state = 'naming_first'
            out += '\n\n' + c('Your troop is empty! Let\'s recruit your first goop!', YLW)
            return out, c('Name your first goop (Enter for random): ', CYN)
        else:
            self.state = 'menu'
            out += '\n\n' + c(random.choice(IDLE_LINES), DIM)
            out += '\n\n' + panel(MENU_TEXT, '~ Command Center ~', GRN)
            return out, c('Command> ', YLW)

    def process(self, line: str):
        """Process input, returns (output, prompt). prompt=None means game over."""
        line = line.strip()

        handler = {
            'naming_first': self._handle_naming_first,
            'menu': self._handle_menu,
            'select_goop': self._handle_select_goop,
            'mission_accept': self._handle_mission_accept,
            'mission_squad': self._handle_mission_squad,
            'naming_recruit': self._handle_naming_recruit,
        }.get(self.state)

        if handler:
            return handler(line)
        return c('Something went wrong. Resetting to menu.', RED), self._go_menu()

    def _go_menu(self):
        self.state = 'menu'
        self.troop.tick_all()
        self.troop.save()
        return c('Command> ', YLW)

    def _menu_output(self):
        return c(random.choice(IDLE_LINES), DIM) + '\n\n' + panel(MENU_TEXT, '~ Command Center ~', GRN)

    def _handle_naming_first(self, line):
        name = line if line else None
        g = self.troop.recruit(name)
        out = c(f'\nWelcome, {g.name}!', GRN) + '\n'
        out += format_goop_detail(g)
        self.troop.save()
        out += '\n\n' + self._menu_output()
        return out, self._go_menu()

    def _handle_menu(self, line):
        if line == '1':
            out = '\n' + format_troop_table(self.troop)
            out += '\n\n' + self._menu_output()
            return out, self._go_menu()

        elif line == '2':
            if not self.troop.goops:
                return c('No goops to inspect!', RED) + '\n' + self._menu_output(), self._go_menu()
            self.state = 'select_goop'
            self.pending_action = 'inspect'
            out = c('Select a goop to inspect:', BOLD) + '\n' + goop_list(self.troop)
            return out, c('Goop #> ', YLW)

        elif line == '3':
            if not self.troop.alive_goops:
                return c('No living goops to feed!', RED) + '\n' + self._menu_output(), self._go_menu()
            self.state = 'select_goop'
            self.pending_action = 'feed'
            out = c('Select a goop to feed:', BOLD) + '\n' + goop_list(self.troop)
            return out, c('Goop #> ', YLW)

        elif line == '4':
            if not self.troop.alive_goops:
                return c('No living goops to train!', RED) + '\n' + self._menu_output(), self._go_menu()
            self.state = 'select_goop'
            self.pending_action = 'train'
            out = c('Select a goop to train:', BOLD) + '\n' + goop_list(self.troop)
            return out, c('Goop #> ', YLW)

        elif line == '5':
            if not self.troop.alive_goops:
                return c('No living goops to rest!', RED) + '\n' + self._menu_output(), self._go_menu()
            self.state = 'select_goop'
            self.pending_action = 'rest'
            out = c('Select a goop to rest:', BOLD) + '\n' + goop_list(self.troop)
            return out, c('Goop #> ', YLW)

        elif line == '6':
            if not self.troop.alive_goops:
                return c('No living goops for a mission!', RED) + '\n' + self._menu_output(), self._go_menu()
            mission = Mission.generate(self.troop.troop_power)
            self.pending_mission = mission
            self.state = 'mission_accept'
            skull = chr(0x1F480)
            out = '\n' + panel(
                f'{BOLD}{mission.name}{RST}\n\n'
                f'{mission.description}\n\n'
                f'Difficulty: {skull * mission.difficulty}\n'
                f'Reward: {mission.reward_bucks} GoopBucks, {mission.reward_xp} XP\n'
                f'Reputation: +{mission.reputation_gain}',
                '~ Mission Available ~', RED
            )
            return out, c('Accept mission? (y/n): ', YLW)

        elif line == '7':
            cost = 20 + len(self.troop.goops) * 10
            if self.troop.goop_bucks < cost:
                out = c(f'Recruitment costs {cost} GoopBucks. You only have {self.troop.goop_bucks}.', RED)
                out += '\n' + self._menu_output()
                return out, self._go_menu()
            self.state = 'naming_recruit'
            return c(f'Recruitment costs {cost} GoopBucks. You have {self.troop.goop_bucks}.', YLW), c('Name (Enter for random): ', CYN)

        elif line == '8':
            out = self._random_event()
            out += '\n\n' + self._menu_output()
            return out, self._go_menu()

        elif line in ('9', 'q', 'quit', 'exit'):
            self.troop.save()
            out = c('Troop saved! Your goops will wait for you... droopily.', GRN)
            out += '\n' + c('(Your save persists in browser localStorage)', DIM)
            out += '\n\n' + self._menu_output()
            return out, self._go_menu()

        else:
            return c('Unknown command! Try a number 1-9.', RED), c('Command> ', YLW)

    def _handle_select_goop(self, line):
        alive = self.troop.alive_goops
        try:
            idx = int(line) - 1
            if not (0 <= idx < len(alive)):
                raise ValueError
            goop = alive[idx]
        except (ValueError, IndexError):
            return c('Invalid choice!', RED) + '\n' + self._menu_output(), self._go_menu()

        action = self.pending_action
        self.pending_action = None

        if action == 'inspect':
            out = '\n' + format_goop_detail(goop)
        elif action == 'feed':
            result = goop.feed()
            out = c(result, GRN)
        elif action == 'train':
            result = goop.train()
            out = c(result, CYN)
        elif action == 'rest':
            result = goop.rest()
            out = c(result, BLU)
        else:
            out = c('Unknown action!', RED)

        out += '\n\n' + self._menu_output()
        self.troop.save()
        return out, self._go_menu()

    def _handle_mission_accept(self, line):
        if line.lower() not in ('y', 'yes'):
            self.pending_mission = None
            out = c('Mission declined. The goops look relieved.', DIM)
            out += '\n\n' + self._menu_output()
            return out, self._go_menu()

        self.state = 'mission_squad'
        alive = self.troop.alive_goops
        out = c('Select goops for the mission (comma-separated numbers, or "all"):', BOLD)
        out += '\n' + goop_list(self.troop)
        return out, c('Squad> ', YLW)

    def _handle_mission_squad(self, line):
        alive = self.troop.alive_goops
        mission = self.pending_mission

        if line.lower() == 'all':
            squad = alive
        else:
            try:
                indices = [int(x.strip()) - 1 for x in line.split(',')]
                squad = [alive[i] for i in indices if 0 <= i < len(alive)]
            except (ValueError, IndexError):
                squad = []

        if not squad:
            self.pending_mission = None
            out = c('No valid goops selected! Mission cancelled.', RED)
            out += '\n\n' + self._menu_output()
            return out, self._go_menu()

        won, log = run_mission(self.troop, squad, mission)
        self.pending_mission = None

        color = GRN if won else RED
        log_text = '\n'.join(log)
        title = 'VICTORY' if won else 'DEFEAT'
        out = '\n' + panel(log_text, f'~ Mission Report: {title} ~', color)
        self.troop.save()
        out += '\n\n' + self._menu_output()
        return out, self._go_menu()

    def _handle_naming_recruit(self, line):
        name = line if line else None
        try:
            goop = self.troop.recruit(name)
            out = c(f'\n{goop.name} has joined the troop!', GRN) + '\n'
            out += format_goop_detail(goop)
        except ValueError as e:
            out = c(str(e), RED)

        self.troop.save()
        out += '\n\n' + self._menu_output()
        return out, self._go_menu()

    def _random_event(self):
        events = [
            ("goop_rain", "A goop rain falls! All goops gain goopiness!"),
            ("tax", "The Goop Tax Collector arrives! -15 GoopBucks."),
            ("gift", "A mysterious blob leaves a gift! +30 GoopBucks!"),
            ("droop_wave", "A droop wave hits! All goops get droopier."),
            ("morale_boost", "A traveling goop bard sings! Morale boost!"),
            ("wild_goop", "A wild goop appears and wants to join!"),
            ("earthquake", "A slime quake! Some goops take damage!"),
            ("feast", "You find a cache of goop food! Hunger reduced!"),
        ]
        event_id, message = random.choice(events)
        out = '\n' + panel(message, '~ Random Event ~', MAG)

        troop = self.troop
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
                from art import random_goop_name
                wild = Goop(
                    name=f"Wild {random_goop_name()[:6]}",
                    level=random.randint(1, 3),
                    attack=random.randint(8, 18),
                    defense=random.randint(3, 12),
                    goopiness=random.randint(50, 90),
                )
                troop.goops.append(wild)
                out += '\n  ' + c(f'{wild.name} joined your troop!', GRN)
            else:
                out += '\n  ' + c('Your troop is full! The wild goop wanders off sadly.', YLW)
        elif event_id == "earthquake":
            for g in troop.alive_goops:
                if random.random() < 0.5:
                    dmg = random.randint(5, 15)
                    g.take_damage(dmg)
        elif event_id == "feast":
            for g in troop.alive_goops:
                g.hunger = max(0, g.hunger - random.randint(15, 30))

        troop.save()
        return out
