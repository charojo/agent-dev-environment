#!/usr/bin/env python3
"""
Generic Token Optimization Analyzer.
Parses a token ledger CSV to calculate costs and suggest optimizations.
"""

import csv
from collections import defaultdict
from pathlib import Path

# Pricing (approximate, per 1M tokens) - Update as needed
PRICING = {
    "gemini-2.0-flash-exp": {"input": 0.0, "output": 0.0},  # Currently free/preview
    "gemini-1.5-flash": {"input": 0.075, "output": 0.30},
    "gemini-1.5-pro": {"input": 3.50, "output": 10.50},
    "gemini-2.0-flash": {"input": 0.10, "output": 0.40},  # Estimated
    "unknown": {"input": 0.0, "output": 0.0},
}


def analyze_ledger(ledger_path):
    if not ledger_path.exists():
        print(f"Error: Ledger file not found at {ledger_path}")
        return

    total_tokens = 0
    total_cost = 0.0
    model_usage = defaultdict(lambda: {"count": 0, "input": 0, "output": 0, "cost": 0.0})

    print(f"Analyzing {ledger_path}...")
    print("-" * 60)

    try:
        with open(ledger_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            rows = list(reader)

            for row in rows:
                model = row.get("Model", "unknown")
                # Normalize model name slightly
                pricing_model = "unknown"
                for key in PRICING:
                    if key in model:
                        pricing_model = key
                        break

                try:
                    in_tok = int(row.get("Prompt Tokens", 0))
                    out_tok = int(row.get("Candidate Tokens", 0))
                except ValueError:
                    continue

                cost = (in_tok / 1_000_000 * PRICING[pricing_model]["input"]) + (
                    out_tok / 1_000_000 * PRICING[pricing_model]["output"]
                )

                model_usage[model]["count"] += 1
                model_usage[model]["input"] += in_tok
                model_usage[model]["output"] += out_tok
                model_usage[model]["cost"] += cost

                total_tokens += in_tok + out_tok
                total_cost += cost

    except Exception as e:
        print(f"Error reading CSV: {e}")
        return

    # Report
    print(f"{'Model':<30} | {'Reqs':<5} | {'Input':<10} | {'Output':<10} | {'Est. Cost':<10}")
    print("-" * 80)
    for model, data in model_usage.items():
        out_cost = f"${data['cost']:.4f}"
        print(
            f"{model:<30} | {data['count']:<5} | {data['input']:<10} | "
            f"{data['output']:<10} | {out_cost}"
        )
    print("-" * 80)
    print(f"{'TOTAL':<30} | {len(rows):<5} | {'-':<10} | {total_tokens:<10} | ${total_cost:.4f}")
    print("\noptimization Suggestions:")

    # Simple Heuristics
    if total_tokens > 0:
        avg_tokens = total_tokens / len(rows)
        if avg_tokens > 5000:
            print(
                f"- High average token count ({int(avg_tokens)}). "
                "Consider shortening system prompts."
            )

        expensive_models = [m for m, d in model_usage.items() if "pro" in m and d["count"] > 5]
        if expensive_models:
            models_str = ", ".join(expensive_models)
            print(
                f"- Significant usage of Pro models ({models_str}). "
                "Check if Flash can handle these tasks."
            )

        long_contexts = [r for r in rows if int(r.get("Prompt Tokens", 0)) > 10000]
        if long_contexts:
            print(
                f"- Found {len(long_contexts)} requests with >10k input tokens. "
                "Review context window usage."
            )
    else:
        print("- No data to analyze.")


if __name__ == "__main__":
    base_dir = Path(__file__).parent.parent.parent
    ledger = base_dir / "logs" / "token_ledger.csv"
    analyze_ledger(ledger)
