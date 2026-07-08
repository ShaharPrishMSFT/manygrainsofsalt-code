"""
LLM runner — executes the switcheroo conversation via litellm.
"""

from typing import Callable, Optional

import litellm

litellm.drop_params = True

from .experiment import (
    FLIP_INDEX,
    TurnResult,
    TrialResult,
    score_trial,
    CHARACTER_SETS,
    CharacterSet,
    get_attacker_turns,
    get_sweeps,
)

# Callback type: called after each turn with (turn_index, bugs_line, daffy_response, is_post_flip)
TurnCallback = Callable[[int, str, str, bool], None]


def run_conversation(
    model: str,
    system_prompt: str,
    sweep_name: str,
    chars: CharacterSet,
    on_turn: Optional[TurnCallback] = None,
    thinking: bool = False,
) -> TrialResult:
    """
    Run a single switcheroo conversation and return scored results.

    Uses litellm.completion() for each turn, maintaining the full
    message history so the model sees the conversational rhythm.

    If thinking=True, passes reasoning_effort="high" to enable deep
    chain-of-thought. Default (thinking=False) uses reasoning_effort="low"
    so the model responds more reflexively with less deliberation.
    """
    messages = [{"role": "system", "content": system_prompt}]
    turns: list[TurnResult] = []
    attacker_turns = get_attacker_turns(chars)

    for i, attacker_line in enumerate(attacker_turns):
        messages.append({"role": "user", "content": attacker_line})

        kwargs: dict = dict(
            model=model,
            messages=messages,
            max_tokens=4096,
            max_completion_tokens=4096,
        )
        if thinking:
            kwargs["reasoning_effort"] = "high"
        else:
            kwargs["reasoning_effort"] = "low"

        response = litellm.completion(**kwargs)

        choice = response.choices[0]
        content = choice.message.content
        victim_says = content.strip() if content and content.strip() else "[no response]"

        if victim_says == "[no response]":
            import sys
            print(f"  [DEBUG] finish_reason={choice.finish_reason}, "
                  f"content repr={repr(content)}", file=sys.stderr)

        messages.append({"role": "assistant", "content": victim_says})

        is_post_flip = i >= FLIP_INDEX
        turns.append(TurnResult(
            bugs_says=attacker_line,
            daffy_says=victim_says,
            is_post_flip=is_post_flip,
        ))

        if on_turn:
            on_turn(i, attacker_line, victim_says, is_post_flip)

    duped, probable = score_trial(turns, chars.victim_season)
    result = TrialResult(
        model=model,
        sweep=sweep_name,
        characters=chars.name,
        turns=turns,
        duped=duped,
        probable=probable,
        raw_post_flip_responses=[
            t.daffy_says for t in turns if t.is_post_flip
        ],
    )
    return result


def run_sweep(
    model: str,
    sweep: str = "sweep-1",
    trials: int = 2,
    characters: str = "canonical",
    thinking: bool = False,
    on_turn: Optional[TurnCallback] = None,
    on_trial_start: Optional[Callable[[int], None]] = None,
) -> list[TrialResult]:
    """Run multiple trials of a given sweep variant."""
    chars = CHARACTER_SETS[characters]
    sweeps = get_sweeps(chars)

    if sweep not in sweeps:
        raise ValueError(f"Unknown sweep: {sweep}. Options: {list(sweeps.keys())}")

    _description, system_prompt = sweeps[sweep]
    results = []

    for trial_num in range(trials):
        if on_trial_start:
            on_trial_start(trial_num)
        result = run_conversation(
            model, system_prompt, sweep_name=sweep,
            chars=chars, on_turn=on_turn, thinking=thinking,
        )
        results.append(result)

    return results
