_VALID_JSON_ESCAPES = set('"\\/bfnrtu')


def repair_json_backslashes(raw: str) -> str:
    """LLM-emitted JSON containing raw LaTeX source (e.g. "old": "...\\&...")
    routinely fails to double backslashes the way JSON requires. Double any
    backslash that isn't already forming a valid JSON escape, so json.loads
    can parse it as a literal backslash instead of erroring out.
    """
    out = []
    i, n = 0, len(raw)
    while i < n:
        c = raw[i]
        if c == "\\" and i + 1 < n and raw[i + 1] in _VALID_JSON_ESCAPES:
            out.append(raw[i:i + 2])
            i += 2
            continue
        if c == "\\":
            out.append("\\\\")
            i += 1
            continue
        out.append(c)
        i += 1
    return "".join(out)
