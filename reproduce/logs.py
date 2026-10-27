"""Reading the recorder's log, and keeping the machine's name and the user's home folder out of saved logs."""
import re

SUBSCRIBED = re.compile(r"Subscribed to topic '([^']+)'")


def private_hits(folder, host, home):
    """Files under folder (relative paths, sorted) whose bytes contain the host name or the home folder."""
    needles = [s.encode() for s in (host, home) if s]
    hits = []
    for path in sorted(p for p in folder.rglob("*") if p.is_file()):
        data = path.read_bytes()
        if any(n in data for n in needles):
            hits.append(path.relative_to(folder).as_posix())
    return hits


def recorder_state(log_text):
    """From `ros2 bag record` output: the topics it has subscribed to, and whether it says it is recording."""
    return set(SUBSCRIBED.findall(log_text)), "Recording..." in log_text


def redact(text, host, home):
    """Replaces the host name with <host> and the home folder with <home>. Empty names change nothing."""
    if home:
        text = text.replace(home, "<home>")
    if host:
        text = text.replace(host, "<host>")
    return text
