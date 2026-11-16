"""Create an optional provider client using an environment variable only."""
import os


def make_client():
    key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    if not key:
        raise RuntimeError("Set ANTHROPIC_API_KEY to use optional API generation or judging.")
    import anthropic
    return anthropic.Anthropic(api_key=key)
