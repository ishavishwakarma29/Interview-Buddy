"""Merge data_parts/*.jsonl into train.jsonl + test.jsonl, checking every example."""
import glob
import json
import random

SYSTEM_START = "You are InterviewBuddy, a warm but sharp mock interviewer"
LABELS = ["What worked:", "To improve:", "Stronger version:"]

examples = []
for path in sorted(glob.glob("data_parts/part*.jsonl")):
    with open(path) as f:
        for n, line in enumerate(f, 1):
            ex = json.loads(line)  # crashes loudly on broken JSON
            msgs = ex["messages"]
            assert msgs[0]["role"] == "system", f"{path}:{n} must start with system"
            assert msgs[0]["content"].startswith(SYSTEM_START), f"{path}:{n} wrong system prompt"
            assert msgs[-1]["role"] == "assistant", f"{path}:{n} must end with assistant"
            for a, b in zip(msgs[1:], msgs[2:]):
                assert a["role"] != b["role"], f"{path}:{n} roles must alternate"
            examples.append(ex)
    print(f"{path}: ok")

graded = sum(
    all(label in m["content"] for label in LABELS)
    for ex in examples for m in ex["messages"] if m["role"] == "assistant"
)
with_memory = sum("Notes from past sessions:" in ex["messages"][0]["content"] for ex in examples)

random.seed(42)
random.shuffle(examples)
n_test = max(1, len(examples) // 10)  # hold back 10% to check the model after training
test, train = examples[:n_test], examples[n_test:]

for name, rows in [("train.jsonl", train), ("test.jsonl", test)]:
    with open(name, "w") as f:
        for ex in rows:
            f.write(json.dumps(ex, ensure_ascii=False) + "\n")

print(f"\n{len(examples)} conversations -> train.jsonl ({len(train)}), test.jsonl ({len(test)})")
print(f"{graded} graded feedback turns, {with_memory} conversations use memory notes")
