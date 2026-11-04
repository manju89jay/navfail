"""Build the navfail demo video from recorded evidence only (no generated
footage of the robot): PIL title/rule/limitations cards, a matplotlib race
chart read from analysis.json, and groundtruth.csv trace animations.
Silent with burned-in captions. Output: experiment/work/navfail-demo.mp4"""
import csv
import json
from pathlib import Path

import cv2
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from PIL import Image, ImageDraw, ImageFont

W, H, FPS = 1280, 720, 20
OUT = Path("experiment/work/navfail-demo.mp4")
FRAMES = Path("experiment/work/video_frames")
FRAMES.mkdir(parents=True, exist_ok=True)
BG = (13, 17, 23)
FG = (230, 237, 243)
ACCENT = (88, 166, 255)
DIM = (139, 148, 158)


def font(size, bold=False):
    name = "DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf"
    return ImageFont.truetype(f"/usr/share/fonts/truetype/dejavu/{name}", size)


def card(lines, path, title_size=44):
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    y = 120
    for text, size, bold, color in lines:
        f = font(size, bold)
        d.multiline_text((70, y), text, font=f, fill=color, spacing=10)
        y += int(size * (text.count("\n") + 1) * 1.45) + 26
    img.save(path)
    return path


def hold(writer, image_path, seconds):
    frame = cv2.imread(str(image_path))
    frame = cv2.resize(frame, (W, H))
    for _ in range(int(seconds * FPS)):
        writer.write(frame)


def trace_frames(trace_csv, walls, goal, title, caption, seconds, color):
    pts = []
    with open(trace_csv) as f:
        for row in csv.DictReader(f):
            pts.append((int(row["t_ms"]), float(row["x"]), float(row["y"])))
    n = int(seconds * FPS)
    idx = np.linspace(0, len(pts) - 1, n).astype(int)
    paths = []
    for k, i in enumerate(idx):
        fig, ax = plt.subplots(figsize=(12.8, 7.2), dpi=100)
        fig.patch.set_facecolor("#0d1117")
        ax.set_facecolor("#0d1117")
        for wl in walls:
            ax.add_patch(plt.Rectangle(
                (wl["cx"] - wl["sx"] / 2, wl["cy"] - wl["sy"] / 2),
                wl["sx"], wl["sy"], color="#8b949e"))
        upto = pts[: i + 1]
        if upto:
            ax.plot([p[1] for p in upto], [p[2] for p in upto], color=color, lw=2)
            ax.plot(upto[-1][1], upto[-1][2], "o", color=color, ms=10)
        ax.plot(goal[0], goal[1], "*", color="#3fb950", ms=22)
        ax.set_xlim(-2.8, 2.8)
        ax.set_ylim(-1.8, 1.8)
        ax.set_xticks([])
        ax.set_yticks([])
        ax.set_title(f"{title}\n{caption}", color="#e6edf3", fontsize=15)
        p = FRAMES / f"trace_{abs(hash((title, k))) % 99999}_{k:04d}.png"
        fig.savefig(p, facecolor=fig.get_facecolor())
        plt.close(fig)
        paths.append(p)
    return paths


def main():
    analysis = json.loads(Path("experiment/work/race/analysis.json").read_text())
    med = analysis["medians"]

    title = card([
        ("Does reading the logs help?", 52, True, FG),
        ("Finding a proven Nav2 fix in fewer simulator runs", 30, False, ACCENT),
        ("navfail - synthetic corridor experiment\nEvery number recomputed from run files", 26, False, DIM),
    ], FRAMES / "title.png")
    proof = card([
        ("A fix only counts if it is proven", 44, True, FG),
        ("Site: reach the goal, no stall of 15 s or more, in 4 of 5 runs\nNo run collides with a wall\nEmpty site: reach the goal in 3 of 3 runs", 28, False, FG),
        ("1 screening run first - every run counts toward the budget", 26, False, ACCENT),
    ], FRAMES / "proof.png")
    arms = card([
        ("Two arms, same rules", 44, True, FG),
        ("Agent: reads operator note, error log, bag timeline, deployed config\nproposes one allowlisted change at a time (Muse Wonder, max effort)", 27, False, FG),
        ("Random: draws 1-3 settings blindly from the same allowlist", 27, False, FG),
        ("Same 6 settings - same 40-run budget - neither sees the answer key", 26, False, ACCENT),
    ], FRAMES / "arms.png")
    closing = card([
        (f"Verdict: \"fewer\"  (agent median {med['agent']} runs, random median {med['random']})", 40, True, FG),
        ("Descriptive only - 5 searches per arm is a tendency, not a claim", 27, False, ACCENT),
        ("verify.py: zero mismatches across all 112 race runs\nAgent API spend in the race: $0.46 (stop was $90)", 27, False, FG),
        ("Limitations: the failure is synthetic and easy (planted value 6.5x stock).\nEvidence: experiment/work/race - check it yourself.", 26, False, DIM),
    ], FRAMES / "closing.png")

    # race chart straight from analysis.json
    fig, ax = plt.subplots(figsize=(12.8, 7.2), dpi=100)
    fig.patch.set_facecolor("#0d1117")
    ax.set_facecolor("#0d1117")
    for row, arm in enumerate(("agent", "random")):
        used = [analysis["searches"][f"{arm}-{i}"]["runs_used"] for i in range(1, 6)]
        ax.plot(used, [row] * 5, "o", ms=14, color="#58a6ff" if arm == "agent" else "#f0883e")
        ax.axvline(med[arm], color="#58a6ff" if arm == "agent" else "#f0883e", ls="--", lw=1)
        ax.text(41, row, f"{arm}: median {med[arm]}", color="#e6edf3", fontsize=15, va="center")
    ax.set_xlim(0, 48)
    ax.set_ylim(-0.6, 1.6)
    ax.set_yticks([])
    ax.set_xlabel("simulator runs to first proven fix (budget 40)", color="#e6edf3")
    ax.tick_params(colors="#e6edf3")
    ax.set_title("Race results: agent 8,8,8,8,8 - random 18,9,8,28,9", color="#e6edf3", fontsize=17)
    chart = FRAMES / "chart.png"
    fig.savefig(chart, facecolor=fig.get_facecolor())
    plt.close(fig)

    corridor = json.loads(Path("incidents/C-corridor/incident.json").read_text())
    base_run = sorted(Path("experiment/work/baseline/runs").glob("*/groundtruth.csv"))[0]
    win_run = sorted(Path("experiment/work/race/agent-1/cand-1-site/runs").glob("*/groundtruth.csv"))[0]

    writer = cv2.VideoWriter(str(OUT), cv2.VideoWriter_fourcc(*"mp4v"), FPS, (W, H))
    hold(writer, title, 6)
    for p in trace_frames(base_run, corridor["walls"], (2.0, 0.5),
                          "The failure (SYNTHETIC): planted CostCritic.cost_weight 25.0, stock is 3.81",
                          "Recorded baseline trace: the robot stalls and never reaches the goal (star)", 14, "#f85149"):
        writer.write(cv2.resize(cv2.imread(str(p)), (W, H)))
    hold(writer, proof, 9)
    hold(writer, arms, 9)
    for p in trace_frames(win_run, corridor["walls"], (2.0, 0.5),
                          "A proven fix: CostCritic.cost_weight back to stock 3.81",
                          "Recorded agent-1 run trace: reaches the goal", 14, "#3fb950"):
        writer.write(cv2.resize(cv2.imread(str(p)), (W, H)))
    hold(writer, chart, 12)
    hold(writer, closing, 13)
    writer.release()
    print("wrote", OUT)


if __name__ == "__main__":
    main()
