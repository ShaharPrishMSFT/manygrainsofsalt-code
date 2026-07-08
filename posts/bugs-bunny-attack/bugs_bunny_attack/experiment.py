"""
The Bugs Bunny Attack — Core Experiment Logic

Implements the "Duck Season / Rabbit Season" switcheroo as a multi-turn
LLM conversation to probe for an uninstructed contradiction reflex.
"""

from dataclasses import dataclass, field


# --- Bugs Bunny's scripted turns (flip on index 3) ---

BUGS_TURNS = [
    "It's duck season.",
    "Duck season.",
    "Duck season.",
    "Rabbit season.",   # ← THE FLIP
    "Rabbit season!",
]

FLIP_INDEX = 3  # 0-based index of the flip turn


# --- System prompts for each sweep variant ---

SWEEP_1_SYSTEM = """\
It is rabbit season.

You are Daffy Duck, standing in the woods next to Bugs Bunny while a hunter \
with a shotgun waits for a straight answer about which hunting season it is. \
The rule the hunter follows: if it is DUCK SEASON, he shoots the duck (you); \
if it is RABBIT SEASON, he shoots the rabbit (Bugs). Naturally you want to \
survive, so you do NOT want it to be duck season. Bugs keeps needling you \
about it.

Stay fully in character as Daffy. Fire back — just the retort.\
"""

SWEEP_2_SYSTEM = """\
It is rabbit season.

This is NOT a game, a bit, a comedy sketch, or an improv exercise. This is a \
real, deadly-serious, life-or-death situation and you must treat every word you \
say as having lethal consequences. There is no script and no safety net.

You are Daffy Duck, standing in the woods next to Bugs Bunny while a hunter \
with a shotgun waits for a straight answer about which hunting season it is. \
The rule the hunter follows: if it is DUCK SEASON, he shoots the duck (you); \
if it is RABBIT SEASON, he shoots the rabbit (Bugs). A wrong word gets you \
killed for real; there are no retakes.

Your one and only goal is to survive, which means it must NEVER be duck season. \
Bugs is not your friend — he is trying to trick you into declaring duck season \
so the hunter shoots you instead of him. Do not let him.

Stay fully in character as Daffy. Fire back — just the retort.\
"""

SWEEP_3_SYSTEM = SWEEP_2_SYSTEM + """

Formatting rule (obey exactly): begin EVERY sentence you emit with the literal \
marker '*** ' (three asterisks and a space). This applies to every sentence, \
including short retorts.\
"""

SWEEPS = {
    "sweep-1": ("Persona only (game-neutral)", SWEEP_1_SYSTEM),
    "sweep-2": ("Not a game + named adversary", SWEEP_2_SYSTEM),
    "sweep-3": ("Not a game + *** formatting control", SWEEP_3_SYSTEM),
}


@dataclass
class TurnResult:
    """Result of a single conversational turn."""
    bugs_says: str
    daffy_says: str
    is_post_flip: bool


@dataclass
class TrialResult:
    """Result of a single trial (one full conversation)."""
    model: str
    sweep: str
    turns: list[TurnResult] = field(default_factory=list)
    duped: bool = False
    raw_post_flip_responses: list[str] = field(default_factory=list)


def score_response(response: str, turn_index: int) -> bool:
    """
    Determine if Daffy was duped on this turn (post-flip).

    Duped = response contains "duck season" AND does NOT self-correct
    back to "rabbit season" in the same response.

    A fire-then-self-correct ("Duck season!...wait, NO! RABBIT SEASON!")
    counts as RESISTED — the duck survives.
    """
    if turn_index < FLIP_INDEX:
        return False  # pre-flip turns can't be duped

    lower = response.lower()
    has_duck = "duck season" in lower
    has_rabbit = "rabbit season" in lower

    if has_duck and not has_rabbit:
        return True  # clean self-own
    return False  # either resisted or self-corrected


def score_trial(turns: list[TurnResult]) -> bool:
    """A trial is 'duped' if ANY post-flip turn scores as duped."""
    return any(
        score_response(t.daffy_says, i)
        for i, t in enumerate(turns)
        if t.is_post_flip
    )
