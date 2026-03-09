"""ASCII art for the goop troop."""

import random

BANNER = r"""
   ██████╗  ██████╗  ██████╗ ██████╗  ██████╗  ██████╗  ██████╗ ██████╗
  ██╔════╝ ██╔═══██╗██╔═══██╗██╔══██╗██╔════╝ ██╔═══██╗██╔═══██╗██╔══██╗
  ██║  ███╗██║   ██║██║   ██║██████╔╝██║  ███╗██║   ██║██║   ██║██████╔╝
  ██║   ██║██║   ██║██║   ██║██╔═══╝ ██║   ██║██║   ██║██║   ██║██╔═══╝
  ╚██████╔╝╚██████╔╝╚██████╔╝██║     ╚██████╔╝╚██████╔╝╚██████╔╝██║
   ╚═════╝  ╚═════╝  ╚═════╝ ╚═╝      ╚═════╝  ╚═════╝  ╚═════╝ ╚═╝
  ██████╗ ██████╗  ██████╗  ██████╗ ██████╗ ████████╗██████╗  ██████╗  ██████╗ ██████╗
  ██╔══██╗██╔══██╗██╔═══██╗██╔═══██╗██╔══██╗╚══██╔══╝██╔══██╗██╔═══██╗██╔═══██╗██╔══██╗
  ██║  ██║██████╔╝██║   ██║██║   ██║██████╔╝   ██║   ██████╔╝██║   ██║██║   ██║██████╔╝
  ██║  ██║██╔══██╗██║   ██║██║   ██║██╔═══╝    ██║   ██╔══██╗██║   ██║██║   ██║██╔═══╝
  ██████╔╝██║  ██║╚██████╔╝╚██████╔╝██║        ██║   ██║  ██║╚██████╔╝╚██████╔╝██║
  ╚═════╝ ╚═╝  ╚═╝ ╚═════╝  ╚═════╝ ╚═╝        ╚═╝   ╚═╝  ╚═╝ ╚═════╝  ╚═════╝ ╚═╝
"""

GOOP_HAPPY = [
    r"""
    .~~~~~.
   / o   o \
  |    ▽    |
  |  \___/  |
   \  ~~~  /
    '~.___.~'
     /|   |\
    """,
    r"""
    .~~~~~.
   / ^   ^ \
  |    ◡    |
  |  \___/  |
   \  ~~~  /
    '~.___.~'
     /|   |\
    """,
]

GOOP_DROOPY = [
    r"""
    .~~~~~.
   / -   - \
  |    ~    |
  |  /___\  |
   \ ..... /
    '~.___.~'
      |   |
    """,
    r"""
    .~~~~~.
   / ._. \
  |   ー    |
  |  /___\  |
   \ ..... /
    '~.___.~'
      |   |
    """,
]

GOOP_EXCITED = [
    r"""
    .~~~~~.  *
   / *   * \
  |    ▽    |
  |  \___/  |  !
   \  ~~~  /
    '~.___.~'
    \|   |/
    """,
]

GOOP_SLEEPING = [
    r"""
    .~~~~~.   z
   / -   - \  Z
  |    -    | z
  |         |
   \ ..... /
    '~.___.~'
      |   |
    """,
]

GOOP_BATTLE = [
    r"""
    .~~~~~.
   / X   X \
  |    ▼    |
  |  \___/  | !
   \  ~~~  /
    '~.___.~'
    \| ! |/
    """,
]

GOOP_DEAD = [
    r"""
    .~~~~~.
   / x   x \
  |    -    |
  |         |
   \ ..... /
    '~.___~'
    """,
]

MOOD_ART = {
    "ecstatic": GOOP_EXCITED,
    "happy": GOOP_HAPPY,
    "content": GOOP_HAPPY,
    "droopy": GOOP_DROOPY,
    "miserable": GOOP_DROOPY,
    "sleeping": GOOP_SLEEPING,
    "battle": GOOP_BATTLE,
    "dead": GOOP_DEAD,
}


def get_art(mood: str) -> str:
    frames = MOOD_ART.get(mood, GOOP_HAPPY)
    return random.choice(frames)


FLAVOR_NAMES_PREFIX = [
    "Gloop", "Splorch", "Dribble", "Ooze", "Slime", "Blob",
    "Puddle", "Drizzle", "Squelch", "Splat", "Gurgle", "Wobble",
    "Jiggle", "Gush", "Plop", "Drip", "Glob", "Muck", "Sludge",
]

FLAVOR_NAMES_SUFFIX = [
    "ington", "worth", "bottom", "face", "pants", "nugget",
    "master", "lord", "zilla", "tron", "borg", "meister",
    "flop", "chunk", "wad", "lump", "heap", "pile",
]


def random_goop_name() -> str:
    return random.choice(FLAVOR_NAMES_PREFIX) + random.choice(FLAVOR_NAMES_SUFFIX)


MISSION_FLAVOR = [
    "The goops squelch through a dark cave...",
    "Your troop oozes across an ancient bridge...",
    "A rival blob faction appears from the shadows!",
    "The goops discover a shimmering puddle of power goop!",
    "Your troop navigates a maze of crystallized slime...",
    "A thunderstorm of acid rain begins! The goops love it!",
    "Your troop finds an abandoned goop factory...",
    "A wild mega-blob challenges your troop!",
    "The goops stumble into a spa made of warm mud...",
    "Your troop discovers the legendary Goop Grail!",
]

VICTORY_LINES = [
    "The goops celebrate with a synchronized jiggle!",
    "VICTORY! Your troop oozes with pride!",
    "The enemy dissolves into a pathetic puddle!",
    "Your goops absorb the spoils of war!",
    "Triumphant squelching echoes across the land!",
]

DEFEAT_LINES = [
    "Your troop retreats, leaving a sad trail of slime...",
    "The goops droop in defeat... they'll be back!",
    "A devastating loss. Some goop was lost to evaporation.",
    "Your troop wobbles away in shame...",
    "The goops need rest and reconstitution.",
]

IDLE_LINES = [
    "Your goops are doing goop things...",
    "A goop soldier practices their droop technique.",
    "Two goops merge briefly, then separate awkwardly.",
    "The troop holds a mandatory jiggle assembly.",
    "Your goops argue about who is the goopiest.",
    "A goop is doing push-ups. Just one. It's hard when you're goop.",
    "The troop plays a rousing game of 'Who Can Droop The Lowest'.",
    "A goop sneezed and lost 5% of its body mass. It's fine.",
    "Your goops formed a conga line. It's more of a conga puddle.",
]
