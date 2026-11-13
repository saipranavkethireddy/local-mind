"""Measure local LLM speed through Ollama. Run:  python benchmark.py [model]
Prints a markdown table you can paste into the README."""
import json
import platform
import sys
import time

import httpx

OLLAMA = "http://127.0.0.1:11434"
MODEL = sys.argv[1] if len(sys.argv) > 1 else "llama3"
PROMPT = "Explain in about 150 words why on-device AI helps protect privacy."


def run_once():
    t0 = time.perf_counter()
    first = None
    final = {}
    with httpx.stream("POST", f"{OLLAMA}/api/chat", timeout=600, json={
        "model": MODEL, "stream": True,
        "options": {"temperature": 0.1},
        "messages": [{"role": "user", "content": PROMPT}],
    }) as r:
        r.raise_for_status()
        for line in r.iter_lines():
            if not line:
                continue
            obj = json.loads(line)
            if first is None and obj.get("message", {}).get("content"):
                first = time.perf_counter() - t0
            if obj.get("done"):
                final = obj
    tps = final["eval_count"] / (final["eval_duration"] / 1e9)
    return first, tps, final["eval_count"]


def main():
    print("Warm-up (loads the model)...")
    run_once()
    results = [run_once() for _ in range(3)]
    ttft = sum(r[0] for r in results) / 3
    tps = sum(r[1] for r in results) / 3
    print("\n| Metric | Value |\n|---|---|")
    print(f"| Machine | {platform.processor() or platform.machine()} / {platform.system()} |")
    print(f"| Model | {MODEL} |")
    print(f"| Time to first token | {ttft:.2f} s |")
    print(f"| Generation speed | {tps:.1f} tokens/s |")


if __name__ == "__main__":
    main()