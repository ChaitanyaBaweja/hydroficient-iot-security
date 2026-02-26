"""
demo_sensor_log.py - Simulates Maya's 3-day sensor capture log

Creates a realistic terminal output showing sensor messages scrolling
by -- the kind of thing you'd see if you left a logger running on the
Grand Marina's water monitoring pipeline.

Usage:
    python demo_sensor_log.py                  (~20 seconds, best for GIF)
    python demo_sensor_log.py --count 4847     (full 4,847 messages, ~2 min)
    python demo_sensor_log.py --speed slow     (readable pace)

The default runs ~300 messages in about 20 seconds, showing the key
beats: header, JSON samples, fast scrolling, day transitions, and the
closing summary. Use --count 4847 for the full simulation.

Tip: Record your terminal, run this script, then convert to GIF.
"""

import json
import time
import random
import sys
import argparse
from datetime import datetime, timedelta, timezone

# =============================================================================
# Configuration
# =============================================================================
FULL_COUNT = 4847
DURATION_DAYS = 3

# Grand Marina sensor fleet
SENSORS = [
    {"id": "grandmarina-sensor-001", "location": "Main Supply Line", "type": "pressure"},
    {"id": "grandmarina-sensor-002", "location": "Building A - Floor 1", "type": "pressure"},
    {"id": "grandmarina-sensor-003", "location": "Building A - Floor 5", "type": "flow"},
    {"id": "grandmarina-sensor-004", "location": "Building B - Basement", "type": "pressure"},
    {"id": "grandmarina-sensor-005", "location": "Building B - Floor 3", "type": "flow"},
    {"id": "grandmarina-sensor-006", "location": "Pool Filtration", "type": "flow"},
    {"id": "grandmarina-sensor-007", "location": "Kitchen Main", "type": "pressure"},
    {"id": "grandmarina-sensor-008", "location": "Laundry Facility", "type": "flow"},
    {"id": "grandmarina-sensor-009", "location": "Irrigation System", "type": "flow"},
    {"id": "grandmarina-sensor-010", "location": "Fire Suppression", "type": "pressure"},
]

# ANSI colors
GRAY = "\033[90m"
WHITE = "\033[97m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
RED = "\033[91m"
BOLD = "\033[1m"
DIM = "\033[2m"
RESET = "\033[0m"


# =============================================================================
# Message Generation
# =============================================================================
def generate_message(timestamp, msg_num):
    """Generate a realistic sensor reading."""
    sensor = random.choice(SENSORS)

    if sensor["type"] == "pressure":
        pressure = round(random.gauss(62.0, 3.5), 1)
        flow = round(random.gauss(45.0, 5.0), 1)
    else:
        pressure = round(random.gauss(58.0, 2.5), 1)
        flow = round(random.gauss(52.0, 8.0), 1)

    pressure = max(35.0, min(85.0, pressure))
    flow = max(5.0, min(95.0, flow))

    message = {
        "device_id": sensor["id"],
        "location": sensor["location"],
        "pressure_psi": pressure,
        "flow_rate_gpm": flow,
        "timestamp": timestamp.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "status": "operational"
    }

    return message, sensor


def format_json_colored(msg):
    """Format JSON with syntax coloring for terminal display."""
    lines = json.dumps(msg, indent=2).split("\n")
    colored = []
    for line in lines:
        if '": "' in line:
            key, val = line.split('": ', 1)
            colored.append(f"{CYAN}{key}\": {GREEN}{val}{RESET}")
        elif '": ' in line:
            key, val = line.split('": ', 1)
            colored.append(f"{CYAN}{key}\": {YELLOW}{val}{RESET}")
        elif line.strip() in ("{", "}", "{}", "},"):
            colored.append(f"{WHITE}{line}{RESET}")
        else:
            colored.append(f"{WHITE}{line}{RESET}")
    return "\n".join(colored)


# =============================================================================
# Display Functions
# =============================================================================
def print_header():
    """Print the logger startup banner."""
    print(f"\n{BOLD}{WHITE}{'=' * 64}{RESET}")
    print(f"{BOLD}{WHITE}  HYDROLOGIC Message Logger -- Grand Marina Hotel{RESET}")
    print(f"{BOLD}{WHITE}{'=' * 64}{RESET}")
    print(f"{DIM}  Broker:    localhost:8883 (mTLS){RESET}")
    print(f"{DIM}  Topic:     hydroficient/grandmarina/#  {RESET}")
    print(f"{DIM}  Started:   Thursday 22:00 local{RESET}")
    print(f"{DIM}  Duration:  3 days continuous capture{RESET}")
    print(f"{BOLD}{WHITE}{'=' * 64}{RESET}")
    print(f"\n{GREEN}[CONNECTED]{RESET} Subscribed to hydroficient/grandmarina/#")
    print(f"{GREEN}[LISTENING]{RESET} Capturing all messages...\n")


def print_message_compact(msg_num, total, msg, sensor, timestamp):
    """One-line compact format for the fast-scrolling bulk."""
    ts = timestamp.strftime("%Y-%m-%d %H:%M:%S")
    device_short = msg["device_id"].replace("grandmarina-", "")
    psi = msg["pressure_psi"]
    gpm = msg["flow_rate_gpm"]
    loc = sensor["location"]

    counter = f"{DIM}[{msg_num:>5}/{total}]{RESET}"
    time_str = f"{DIM}{ts}{RESET}"
    device_str = f"{CYAN}{device_short:<12}{RESET}"
    location_str = f"{DIM}{loc:<22}{RESET}"
    readings = f"{YELLOW}{psi:>5.1f} PSI{RESET} {DIM}|{RESET} {YELLOW}{gpm:>5.1f} GPM{RESET}"

    print(f"  {counter} {time_str}  {device_str} {location_str} {readings}")


def print_message_json(msg_num, total, msg):
    """Full JSON format for occasional expanded views."""
    counter = f"{DIM}[{msg_num}/{total}]{RESET}"
    topic_suffix = msg["device_id"].split("-")[-1]
    print(f"\n  {counter} {GREEN}CAPTURED{RESET} on topic: {CYAN}hydroficient/grandmarina/{topic_suffix}/sensors{RESET}")
    for line in format_json_colored(msg).split("\n"):
        print(f"    {line}")
    print()


def print_day_marker(day_num, timestamp):
    """Print a visual separator between days."""
    date_str = timestamp.strftime("%A, %B %d")
    print(f"\n  {BOLD}{WHITE}{'-' * 56}{RESET}")
    print(f"  {BOLD}{WHITE}  Day {day_num} -- {date_str}{RESET}")
    print(f"  {BOLD}{WHITE}{'-' * 56}{RESET}\n")


def print_skip_marker(skipped, next_num, total):
    """Show that messages were skipped (for short mode)."""
    print(f"\n  {DIM}  ... [{skipped:,} messages scrolling by] ...{RESET}\n")


def print_summary(total, start_time, end_time):
    """Print the final capture summary."""
    duration = end_time - start_time
    hours = duration.total_seconds() / 3600

    print(f"\n{BOLD}{WHITE}{'=' * 64}{RESET}")
    print(f"{BOLD}{WHITE}  CAPTURE COMPLETE{RESET}")
    print(f"{BOLD}{WHITE}{'=' * 64}{RESET}")
    print(f"  {WHITE}Total messages:  {BOLD}{YELLOW}{total:,}{RESET}")
    print(f"  {WHITE}Duration:        {BOLD}{hours:.1f} hours ({duration.days} days){RESET}")
    print(f"  {WHITE}Unique devices:  {BOLD}10{RESET}")
    print(f"  {WHITE}Avg msg/hour:    {BOLD}{total / hours:.0f}{RESET}")
    print(f"  {WHITE}Saved to:        {BOLD}{GREEN}captured_messages.json{RESET}")
    print(f"{BOLD}{WHITE}{'=' * 64}{RESET}")

    # The hook
    print(f"\n  {DIM}Every one of these messages was accepted by the subscriber.{RESET}")
    print(f"  {DIM}Not one was checked for freshness, sequence, or integrity.{RESET}")
    print(f"  {DIM}Any of them could be replayed.{RESET}\n")


# =============================================================================
# Simulation Modes
# =============================================================================
def run_simulation(display_count, speed="fast"):
    """
    Run the sensor log simulation.

    display_count: how many messages to actually print (rest are skipped).
                   The summary always shows the real total (4,847).
    """
    # Timing config
    if speed == "fast":
        compact_delay = 0.008
        json_delay = 0.5
        day_delay = 0.8
        batch_size = 60
    elif speed == "slow":
        compact_delay = 0.04
        json_delay = 1.5
        day_delay = 2.0
        batch_size = 20
    else:  # medium
        compact_delay = 0.015
        json_delay = 0.8
        day_delay = 1.2
        batch_size = 40

    full_mode = (display_count >= FULL_COUNT)

    # Simulate 3 days starting Thursday night
    start_time = datetime(2024, 1, 11, 22, 0, 0, tzinfo=timezone.utc)
    end_time = start_time + timedelta(days=DURATION_DAYS)
    time_step = (end_time - start_time).total_seconds() / FULL_COUNT

    print_header()
    time.sleep(day_delay)

    if full_mode:
        # Full simulation: print every message
        current_day = 0
        for i in range(1, FULL_COUNT + 1):
            current_time = start_time + timedelta(seconds=time_step * i)
            day = (current_time - start_time).days + 1

            if day > current_day:
                current_day = day
                print_day_marker(current_day, current_time)
                time.sleep(day_delay)

            msg, sensor = generate_message(current_time, i)

            if i <= 3 or (i % batch_size == 0 and i < FULL_COUNT - 50):
                print_message_json(i, FULL_COUNT, msg)
                time.sleep(json_delay)
            else:
                print_message_compact(i, FULL_COUNT, msg, sensor, current_time)
                time.sleep(compact_delay)

            # Accelerate in the last 30%
            if i > FULL_COUNT * 0.7:
                compact_delay = max(0.003, compact_delay * 0.999)
    else:
        # Short mode: show key beats, skip the middle
        # Beat 1: First 3 messages as JSON (sets the visual tone)
        print_day_marker(1, start_time + timedelta(hours=1))
        time.sleep(day_delay)

        for i in range(1, 4):
            current_time = start_time + timedelta(seconds=time_step * i)
            msg, sensor = generate_message(current_time, i)
            print_message_json(i, FULL_COUNT, msg)
            time.sleep(json_delay)

        # Beat 2: Fast scroll of ~100 compact messages (Day 1)
        msgs_in_beat2 = min(100, display_count // 3)
        for i in range(4, 4 + msgs_in_beat2):
            current_time = start_time + timedelta(seconds=time_step * i)
            msg, sensor = generate_message(current_time, i)
            print_message_compact(i, FULL_COUNT, msg, sensor, current_time)
            time.sleep(compact_delay)

        # Beat 3: Skip marker + Day 2
        skip_to = FULL_COUNT // 3
        print_skip_marker(skip_to - (4 + msgs_in_beat2), skip_to, FULL_COUNT)
        time.sleep(0.4)

        day2_start = start_time + timedelta(days=1)
        print_day_marker(2, day2_start)
        time.sleep(day_delay)

        # Beat 4: More fast scroll (~80 messages)
        msgs_in_beat4 = min(80, display_count // 3)
        for j in range(msgs_in_beat4):
            i = skip_to + j
            current_time = start_time + timedelta(seconds=time_step * i)
            msg, sensor = generate_message(current_time, i)

            if j == 30:
                print_message_json(i, FULL_COUNT, msg)
                time.sleep(json_delay)
            else:
                print_message_compact(i, FULL_COUNT, msg, sensor, current_time)
                time.sleep(compact_delay)

        # Beat 5: Skip marker + Day 3
        skip_to2 = FULL_COUNT * 2 // 3
        print_skip_marker(skip_to2 - (skip_to + msgs_in_beat4), skip_to2, FULL_COUNT)
        time.sleep(0.4)

        day3_start = start_time + timedelta(days=2)
        print_day_marker(3, day3_start)
        time.sleep(day_delay)

        # Beat 6: Final fast scroll approaching 4847, accelerating
        remaining = display_count - msgs_in_beat2 - msgs_in_beat4 - 3
        remaining = max(remaining, 60)
        final_start = FULL_COUNT - remaining
        for j in range(remaining):
            i = final_start + j
            current_time = start_time + timedelta(seconds=time_step * i)
            msg, sensor = generate_message(current_time, i)
            print_message_compact(i, FULL_COUNT, msg, sensor, current_time)
            # Accelerate toward the end
            delay = max(0.003, compact_delay * (1 - j / remaining * 0.7))
            time.sleep(delay)

        # Final message
        current_time = end_time - timedelta(seconds=10)
        msg, sensor = generate_message(current_time, FULL_COUNT)
        print_message_compact(FULL_COUNT, FULL_COUNT, msg, sensor, current_time)
        time.sleep(0.3)

    # Summary always shows the real total
    time.sleep(day_delay)
    print_summary(FULL_COUNT, start_time, end_time)


# =============================================================================
# Entry Point
# =============================================================================
def main():
    parser = argparse.ArgumentParser(
        description="Simulate Maya's 3-day sensor capture log",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python demo_sensor_log.py                  Short demo (~20 sec, best for GIF)
    python demo_sensor_log.py --count 4847     Full 4,847 messages (~2 min)
    python demo_sensor_log.py --speed slow     Readable pace
        """
    )
    parser.add_argument(
        "--speed",
        choices=["fast", "medium", "slow"],
        default="fast",
        help="Scroll speed (default: fast)"
    )
    parser.add_argument(
        "--count",
        type=int,
        default=300,
        help="Messages to display (default: 300 for ~20sec GIF, use 4847 for full)"
    )
    args = parser.parse_args()

    try:
        run_simulation(args.count, args.speed)
    except KeyboardInterrupt:
        print(f"\n\n  {YELLOW}[STOPPED]{RESET} Capture interrupted.\n")
        sys.exit(0)


if __name__ == "__main__":
    main()
