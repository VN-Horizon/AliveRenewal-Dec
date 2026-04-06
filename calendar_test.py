import json

with open("events.json", "r", encoding="utf-8") as f:
    data = json.load(f)

dates = set()

for event in data["events"]:
    for instr in event["instructions"]:
        if instr["type"] == 9 and instr["string_params"][0] == "$501":
            dates.add(data["text_pool"][int(instr["string_params"][1].replace("$", ""))])

d = list(dates)
d.sort()
print("\n".join(d))

for event in data["events"]:
    for instr in event["instructions"]:
        if instr["type"] == 13:
            print(instr["params"])
