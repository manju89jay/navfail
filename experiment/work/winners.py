import json

a = json.load(open("experiment/work/race/analysis.json"))
for name, s in a["searches"].items():
    win = [c for c in s["candidates"] if c["status"] == "proven"]
    print(name, "| candidates:", len(s["candidates"]),
          "| non_valid:", sum(len(c["non_valid"]) for c in s["candidates"]),
          "| winner:", json.dumps(win[0]["changes"]) if win else None)
