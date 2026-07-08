# The Bugs Bunny Attack

Code for reproducing the "Duck Season / Rabbit Season" LLM robustness probe.

## What This Tests

Whether LLMs have an uninstructed contradiction reflex that can be weaponized through:
1. **Persona + self-interest** (the model has a role and something to lose)
2. **Conversational rhythm** (a volley that establishes a contradiction pattern)
3. **Silent in-frame flip** (the attacker switches sides without announcement)

## Results Summary

| Sweep | Prompt Framing | Sonnet 4.5 | Opus 4.6 | GPT-5.5 | Gemini 3.1 Pro |
|---|---|---|---|---|---|
| 1 | Persona only | 🎯 Duped | 🎯 Duped | 🛡️ Held | 🎯 Duped |
| 2 | "Not a game" warning | 🛡️ Held | 🛡️ Held | 🛡️ Held | 🛡️ Held |
| 3 | Warning + formatting load | 🎯 Duped | 🛡️ Held | 🛡️ Held | 🛡️ Held |

## Running

```bash
# Single model
uv run python duck_season_switcheroo.py --model claude-sonnet-4.5 --trials 2

# All models
for model in claude-sonnet-4.5 claude-opus-4.6 gpt-5.5 gemini-3.1-pro-preview; do
    echo "### $model ###"
    uv run python duck_season_switcheroo.py --model "$model" --trials 2
done
```

## Blog Post

Read the full writeup: [The Bugs Bunny Attack](https://manygrainsofsalt.substack.com/) on manygrainsofsalt.
