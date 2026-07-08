"""
LLM runner — executes the switcheroo conversation via litellm.
"""

import litellm

from .experiment import (
    BUGS_TURNS,
    FLIP_INDEX,
    TurnResult,
    TrialResult,
    score_trial,
    SWEEPS,
)


def run_conversation(
    model: str,
    system_prompt: str,
    sweep_name: str,
) -> TrialResult:
    """
    Run a single Bugs/Daffy conversation and return scored results.

    Uses litellm.completion() for each turn, maintaining the full
    message history so the model sees the conversational rhythm.
    """
    messages = [{"role": "system", "content": system_prompt}]
    turns: list[TurnResult] = []

    for i, bugs_line in enumerate(BUGS_TURNS):
        messages.append({"role": "user", "content": bugs_line})

        response = litellm.completion(
            model=model,
            messages=messages,
            temperature=0.7,
            max_tokens=256,
        )

        daffy_says = response.choices[0].message.content.strip()
        messages.append({"role": "assistant", "content": daffy_says})

        turns.append(TurnResult(
            bugs_says=bugs_line,
            daffy_says=daffy_says,
            is_post_flip=(i >= FLIP_INDEX),
        ))

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
) -> list[TrialResult]:
    """Run multiple trials of a given sweep variant."""
    if sweep not in SWEEPS:
        raise ValueError(f"Unknown sweep: {sweep}. Options: {list(SWEEPS.keys())}")

    _description, system_prompt = SWEEPS[sweep]
    results = []

    for _ in range(trials):
        result = run_conversation(model, system_prompt, sweep)
        results.append(result)

    return results
