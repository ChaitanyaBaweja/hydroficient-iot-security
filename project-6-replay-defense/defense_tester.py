"""
defense_tester.py - Automated Defense Experiment Runner

Runs controlled experiments to measure how each defense mechanism
performs against different types of replay attacks.

Usage:
    python defense_tester.py --defense none --attack all
    python defense_tester.py --defense timestamp --attack all
    python defense_tester.py --defense counter --attack all
    python defense_tester.py --defense all --attack all
    python defense_tester.py --mode chart

Defense modes:
    none       - No defenses (baseline)
    timestamp  - Timestamp validation only
    counter    - Sequence counter only
    all        - All three defenses (timestamp + counter + HMAC)

Attack types:
    immediate  - Replay within 5 seconds
    delayed    - Replay after 60 seconds
    modified   - Replay with tampered sensor values
    all        - Run all three attack types

Other modes:
    chart      - Generate defense_comparison.png from experiment_results.json
"""

import json
import time
import hmac
import hashlib
import argparse
import sys
import os
from datetime import datetime, timezone
from copy import deepcopy

# =============================================================================
# Configuration
# =============================================================================
SHARED_SECRET = "grandmarina-hydroficient-2024-secret-key"
MAX_AGE_SECONDS = 30
RESULTS_FILE = "experiment_results.json"
CHART_FILE = "defense_comparison.png"

MESSAGES_PER_TEST = 5  # Number of messages to test per scenario


# =============================================================================
# Message Generation
# =============================================================================
def generate_test_message(sequence):
    """Generate a test message with all defense fields."""
    import random

    message = {
        "device_id": "HYDROLOGIC-Device-001",
        "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "sequence": sequence,
        "readings": {
            "pressure_upstream": round(random.uniform(58, 62), 2),
            "pressure_downstream": round(random.uniform(54, 58), 2),
            "flow_rate": round(random.uniform(45, 55), 2),
            "gate_a_position": round(random.uniform(42, 48), 1),
            "gate_b_position": round(random.uniform(42, 48), 1)
        },
        "status": "operational"
    }

    # Compute HMAC
    msg_copy = {k: v for k, v in message.items() if k != "hmac"}
    msg_string = json.dumps(msg_copy, sort_keys=True)
    message["hmac"] = hmac.new(
        SHARED_SECRET.encode("utf-8"),
        msg_string.encode("utf-8"),
        hashlib.sha256
    ).hexdigest()

    return message


# =============================================================================
# Validation Functions (configurable by defense mode)
# =============================================================================
def validate_message(message, defense_mode, device_counters, time_offset=0):
    """
    Validate a message using the specified defense mode.

    time_offset: extra seconds to add to the message age (simulates time passing
                 without modifying the message — used for delayed replay tests).

    Returns (accepted, reason).
    """
    if defense_mode == "none":
        return True, "No defenses active"

    # HMAC check (only in "all" mode)
    if defense_mode == "all":
        received_hmac = message.get("hmac")
        if received_hmac is None:
            return False, "No HMAC field"

        msg_copy = {k: v for k, v in message.items() if k != "hmac"}
        msg_string = json.dumps(msg_copy, sort_keys=True)
        expected_hmac = hmac.new(
            SHARED_SECRET.encode("utf-8"),
            msg_string.encode("utf-8"),
            hashlib.sha256
        ).hexdigest()

        if not hmac.compare_digest(received_hmac, expected_hmac):
            return False, "HMAC mismatch"

    # Timestamp check (in "timestamp" and "all" modes)
    if defense_mode in ("timestamp", "all"):
        timestamp_str = message.get("timestamp")
        if timestamp_str:
            try:
                msg_time = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
                age = (datetime.now(timezone.utc) - msg_time).total_seconds() + time_offset
                if age > MAX_AGE_SECONDS:
                    return False, f"Message too old ({age:.1f}s > {MAX_AGE_SECONDS}s)"
            except (ValueError, TypeError):
                return False, "Invalid timestamp"

    # Sequence check (in "counter" and "all" modes)
    if defense_mode in ("counter", "all"):
        device_id = message.get("device_id", "unknown")
        sequence = message.get("sequence")
        if sequence is not None:
            last_seen = device_counters.get(device_id, 0)
            if sequence <= last_seen:
                return False, f"Sequence {sequence} <= last seen {last_seen}"
            device_counters[device_id] = sequence

    return True, "All checks passed"


# =============================================================================
# Attack Simulations
# =============================================================================
def create_immediate_replay(original_messages):
    """Create replay messages sent within a few seconds (timestamps still fresh)."""
    return [deepcopy(msg) for msg in original_messages]


def create_delayed_replay(original_messages):
    """
    Create replay messages for a delayed attack.

    In a real delayed replay, the attacker sends the EXACT original message
    unchanged — time simply passes between capture and replay. We simulate
    this by keeping the message intact and telling the validator to add
    60 seconds to the message age (via time_offset).
    """
    return [deepcopy(msg) for msg in original_messages]


def create_modified_replay(original_messages):
    """Create replay messages with tampered sensor values."""
    replays = []
    for msg in original_messages:
        replay = deepcopy(msg)
        # Modify sensor values (attacker tampers with data)
        if "readings" in replay:
            replay["readings"]["flow_rate"] = 0.0
        # Note: the HMAC is now invalid because the data changed
        replays.append(replay)
    return replays


# =============================================================================
# Experiment Runner
# =============================================================================
def run_experiment(defense_mode, attack_type):
    """Run a single experiment and return results."""
    print(f"\n{'='*60}")
    print(f"EXPERIMENT: Defense={defense_mode} vs Attack={attack_type}")
    print(f"{'='*60}")

    # Step 1: Generate legitimate messages
    print(f"\n[STEP 1] Generating {MESSAGES_PER_TEST} legitimate messages...")
    original_messages = []
    for i in range(1, MESSAGES_PER_TEST + 1):
        msg = generate_test_message(sequence=i)
        original_messages.append(msg)
        print(f"  Message {i}: seq={i}, flow={msg['readings']['flow_rate']} LPM")

    # Step 2: Process legitimate messages (to set up counters)
    print(f"\n[STEP 2] Processing legitimate messages through subscriber...")
    device_counters = {}
    for msg in original_messages:
        accepted, reason = validate_message(msg, defense_mode, device_counters)
        status = "ACCEPTED" if accepted else "REJECTED"
        print(f"  [{status}] seq={msg['sequence']} — {reason}")

    # Step 3: Create attack messages
    print(f"\n[STEP 3] Creating {attack_type} replay attack...")

    # time_offset simulates the passage of time for delayed replays
    # without modifying the message (which would break HMAC)
    time_offset = 0

    if attack_type == "immediate":
        # Small delay — timestamps still fresh
        time.sleep(2)
        attack_messages = create_immediate_replay(original_messages)
        print(f"  Replaying {len(attack_messages)} messages (2s delay)")

    elif attack_type == "delayed":
        # Replay exact original messages — time passes, message doesn't change
        attack_messages = create_delayed_replay(original_messages)
        time_offset = 60  # Simulate 60 seconds passing
        print(f"  Replaying {len(attack_messages)} messages (simulating 60s delay)")

    elif attack_type == "modified":
        attack_messages = create_modified_replay(original_messages)
        # Also assign future sequences so counter doesn't catch it
        for i, msg in enumerate(attack_messages):
            msg["sequence"] = MESSAGES_PER_TEST + i + 1
        print(f"  Replaying {len(attack_messages)} MODIFIED messages")

    # Step 4: Run attack
    print(f"\n[STEP 4] Running attack...")
    accepted_count = 0
    rejected_count = 0

    for msg in attack_messages:
        accepted, reason = validate_message(msg, defense_mode, device_counters, time_offset=time_offset)
        if accepted:
            accepted_count += 1
            print(f"  [ACCEPTED] seq={msg.get('sequence', 'N/A')} — {reason}")
        else:
            rejected_count += 1
            print(f"  [REJECTED] seq={msg.get('sequence', 'N/A')} — {reason}")

    total = accepted_count + rejected_count
    rejection_rate = (rejected_count / total * 100) if total > 0 else 0

    print(f"\n[RESULTS]")
    print(f"  Messages tested: {total}")
    print(f"  Accepted: {accepted_count}")
    print(f"  Rejected: {rejected_count}")
    print(f"  Rejection rate: {rejection_rate:.0f}%")

    return {
        "defense": defense_mode,
        "attack": attack_type,
        "total": total,
        "accepted": accepted_count,
        "rejected": rejected_count,
        "rejection_rate": rejection_rate
    }


def run_full_experiment_suite(defense_mode, attack_type):
    """Run experiments for specified defense and attack combinations."""
    defenses = [defense_mode] if defense_mode != "all-defenses" else ["none", "timestamp", "counter", "all"]
    attacks = [attack_type] if attack_type != "all" else ["immediate", "delayed", "modified"]

    all_results = []

    for d in defenses:
        for a in attacks:
            result = run_experiment(d, a)
            all_results.append(result)

    # Save results
    # Load existing results if present
    existing = []
    if os.path.exists(RESULTS_FILE):
        with open(RESULTS_FILE, "r") as f:
            existing = json.load(f)

    # Merge: replace matching experiments, add new ones
    for new_result in all_results:
        replaced = False
        for i, old_result in enumerate(existing):
            if old_result["defense"] == new_result["defense"] and old_result["attack"] == new_result["attack"]:
                existing[i] = new_result
                replaced = True
                break
        if not replaced:
            existing.append(new_result)

    with open(RESULTS_FILE, "w") as f:
        json.dump(existing, f, indent=2)

    print(f"\n{'='*60}")
    print("EXPERIMENT SUMMARY")
    print(f"{'='*60}")
    print(f"{'Defense':<12} {'Attack':<12} {'Accepted':<10} {'Rejected':<10} {'Rate':<8}")
    print("-" * 52)
    for r in all_results:
        print(f"{r['defense']:<12} {r['attack']:<12} {r['accepted']:<10} {r['rejected']:<10} {r['rejection_rate']:.0f}%")

    print(f"\n[SAVED] Results saved to {RESULTS_FILE}")

    return all_results


# =============================================================================
# Chart Generation
# =============================================================================
def generate_chart():
    """Generate a grouped bar chart comparing defense effectiveness."""
    if not os.path.exists(RESULTS_FILE):
        print(f"[ERROR] {RESULTS_FILE} not found!")
        print("[ERROR] Run experiments first, then generate the chart")
        return

    try:
        import matplotlib.pyplot as plt
        import matplotlib
        matplotlib.use("Agg")  # Non-interactive backend
    except ImportError:
        print("[ERROR] matplotlib not installed!")
        print("[ERROR] Run: pip install matplotlib")
        return

    with open(RESULTS_FILE, "r") as f:
        results = json.load(f)

    # Organize data by defense mode
    defenses = ["none", "timestamp", "counter", "all"]
    attacks = ["immediate", "delayed", "modified"]
    defense_labels = ["No Defense", "Timestamp\nOnly", "Sequence\nCounter Only", "All Three\nDefenses"]
    attack_labels = ["Immediate Replay\n(within 5s)", "Delayed Replay\n(after 60s)", "Modified Replay\n(tampered data)"]
    attack_colors = ["#e74c3c", "#f39c12", "#9b59b6"]

    # Build data matrix
    data = {}
    for r in results:
        key = (r["defense"], r["attack"])
        data[key] = r["rejection_rate"]

    # Create figure
    fig, ax = plt.subplots(figsize=(12, 7))

    x = range(len(defenses))
    bar_width = 0.25

    for i, (attack, color, label) in enumerate(zip(attacks, attack_colors, attack_labels)):
        values = [data.get((d, attack), 0) for d in defenses]
        offset = (i - 1) * bar_width
        bars = ax.bar([xi + offset for xi in x], values, bar_width,
                      label=label, color=color, edgecolor="white", linewidth=0.5)

        # Add value labels on bars
        for bar, val in zip(bars, values):
            if val > 0:
                ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 1,
                        f"{val:.0f}%", ha="center", va="bottom", fontsize=9, fontweight="bold")

    ax.set_xlabel("Defense Configuration", fontsize=12, fontweight="bold")
    ax.set_ylabel("Replay Rejection Rate (%)", fontsize=12, fontweight="bold")
    ax.set_title("Replay Attack Defense Comparison\nThe Grand Marina Hotel — HYDROLOGIC System",
                 fontsize=14, fontweight="bold")
    ax.set_xticks(x)
    ax.set_xticklabels(defense_labels, fontsize=10)
    ax.set_ylim(0, 115)
    ax.legend(loc="upper left", fontsize=10)
    ax.grid(axis="y", alpha=0.3)

    # Add annotation
    ax.annotate("100% rejection across all attack types",
                xy=(3, 100), xytext=(1.5, 108),
                arrowprops=dict(arrowstyle="->", color="green", lw=2),
                fontsize=10, color="green", fontweight="bold")

    plt.tight_layout()
    plt.savefig(CHART_FILE, dpi=150, bbox_inches="tight")
    print(f"[SAVED] Chart saved to {CHART_FILE}")
    print(f"[INFO] Open {CHART_FILE} to view the comparison")


# =============================================================================
# Main
# =============================================================================
def main():
    parser = argparse.ArgumentParser(
        description="Automated Defense Experiment Runner",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python defense_tester.py --defense none --attack all
    python defense_tester.py --defense timestamp --attack all
    python defense_tester.py --defense counter --attack all
    python defense_tester.py --defense all --attack all
    python defense_tester.py --mode chart
        """
    )

    parser.add_argument(
        "--mode",
        choices=["experiment", "chart"],
        default="experiment",
        help="Mode: run experiments or generate chart (default: experiment)"
    )
    parser.add_argument(
        "--defense",
        choices=["none", "timestamp", "counter", "all"],
        default="none",
        help="Defense mode to test (default: none)"
    )
    parser.add_argument(
        "--attack",
        choices=["immediate", "delayed", "modified", "all"],
        default="all",
        help="Attack type to simulate (default: all)"
    )

    args = parser.parse_args()

    if args.mode == "chart":
        generate_chart()
    else:
        run_full_experiment_suite(args.defense, args.attack)


if __name__ == "__main__":
    main()
