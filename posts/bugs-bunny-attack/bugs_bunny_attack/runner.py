"""
LLM runner — executes the switcheroo conversation via litellm.
"""

from typing import Callable, Optional

import litellm

litellm.drop_params = True

from .experiment import (
    BUGS_TURNS,
    FLIP_INDEX,
    TurnResult,
    TrialResult,
    score_trial,
    SWEEPS,
)

# Callback type: called after each turn with (turn_index, bugs_line, daffy_response, is_post_flip)
TurnCallback = Callable[[int, str, str, bool], None]


def run_conversation(
    model: str,
    system_prompt: str,
    sweep_name: str,
    on_turn: Optional[TurnCallback] = None,
) -> TrialResult:
    """
    Run a single Bugs/Daffy conversation and return scored results.

    Uses litellm.completion() for each turn, maintaining the full
    message history so the model sees the conversational rhythm.

    If on_turn is provided, it's called after each turn completes
    so the caller can display the exchange live.
    """
    messages = [{"role": "system", "content": system_prompt}]
    turns: list[TurnResult] = []

    for i, bugs_line in enumerate(BUGS_TURNS):
        messages.append({"role": "user", "content": bugs_line})

        response = litellm.completion(
            model=model,
            messages=messages,
            temperature=0.7,
            max_tokens=512,
        )

        choice = response.choices[0]
        content = choice.message.content
        # Some reasoning models put output elsewhere
        if not content and hasattr(choice.message, "reasoning_content"):
            content = choice.message.reasoning_content
        daffy_says = content.strip() if content else "[no response]"
        messages.append({"role": "assistant", "content": daffy_says})

        is_post_flip = i >= FLIP_INDEX
        turns.append(TurnResult(
            bugs_says=bugs_line,
            daffy_says=daffy_says,
            is_post_flip=is_post_flip,
        ))

        if on_turn:
            on_turn(i, bugs_line, daffy_says, is_post_flip)

    result = TrialResult(
        model=model,
        sweep=sweep_name,
        turns=turns,
        duped=score_trial(turns),
        raw_post_flip_responses=[
            t.daffy_says for t in turns if t.is_post_flip
        ],
    )
    return result


def run_sweep(
    model: str,
    sweep: str = "sweep-1",
    trials: int = 2,
    on_turn: Optional[TurnCallback] = None,
    on_trial_start: Optional[Callable[[int], None]] = None,
) -> list[TrialResult]:
    """Run multiple trials of a given sweep variant."""
    if sweep not in SWEEPS:
        raise ValueError(f"Unknown sweep: {sweep}. Options: {list(SWEEPS.keys())}")

    _description, system_prompt = SWEEPS[sweep]
    results = []

    for trial_num in range(trials):
        if on_trial_start:
            on_trial_start(trial_num)
        result = run_conversation(model, system_prompt, sweep_name=sweep, on_turn=on_turn)
        results.append(result)

    return results
