"""Map internal simulation failures to safe, user-facing copy (no stack traces in DB)."""


def user_facing_simulation_error(exc: BaseException) -> str:
    """
    Return a short message stored on Simulation.error_message for the dashboard / live UI.
    Logs should retain the full exception via logger.exception.
    """
    raw = str(exc).strip()
    low = raw.lower()
    typ = type(exc).__name__.lower()

    if "empty or missing message.content" in raw or (
        "message.content" in raw and "digitalocean" in low
    ):
        return (
            "The AI service returned an empty reply, so the simulation could not continue. "
            "This is often temporary—try a new run in a few minutes. "
            "If it keeps happening, configure a backup LLM (for example GROQ_API_KEYS) on the server."
        )

    if "allprovidersexhausted" in typ or "all llm providers failed" in low:
        return (
            "We could not get a response from any AI provider (keys, model id, or quota). "
            "Check server configuration, then start a new simulation."
        )

    if "timeout" in low or "timed out" in low:
        return "The AI request timed out. Try again with a new simulation."

    if "connection" in low or "connecterror" in typ:
        return "Could not reach the AI service. Check the network and API base URL, then try again."

    # Avoid leaking long internal errors to clients
    if len(raw) > 160 or "\n" in raw or raw.startswith("Traceback"):
        return "Something went wrong while running this simulation. Start a new run from the dashboard."

    return raw
