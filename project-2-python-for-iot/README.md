# Project 2: Python for IoT Security

Build a mock water sensor data generator using Python in a Jupyter notebook.

## What's New in This Project

Project 1 was conceptual — you identified threats on paper. This project introduces Python programming so you can start working with the same kind of data that real IoT devices produce. Everything you build here (sensor readings, JSON formatting, timestamps) gets used directly in Projects 3 through 7.

## What You'll Build

A mock water sensor data generator that runs in a Jupyter notebook on Google Colab. You'll generate realistic sensor readings — pressure, flow rate, and gate position — and format them as JSON, the same data format used by real IoT devices. By the end, you'll have a reusable function that produces sensor data on demand.

## Concepts Covered

- Python fundamentals: variables, loops, dictionaries, functions
- JSON data format and why IoT systems use it
- Sensor data structures (device ID, timestamp, nested readings)
- Random data generation with realistic variation
- ISO 8601 timestamps and the `datetime` module

## Files in This Project

| File | Description |
|------|-------------|
| `sensor_generator_starter.ipynb` | Jupyter notebook — starter template for building a sensor data generator |

## Prerequisites

- A Google account (for Google Colab — free, no install needed)

## How to Run

1. Open Google Colab: https://colab.research.google.com
2. Click **File > Upload notebook** and select `sensor_generator_starter.ipynb`
3. Run each cell in order by pressing **Shift+Enter** or clicking the play button to the left of the cell
4. Follow the instructions inside each cell — some cells ask you to fill in code before running

## What to Expect

The notebook generates JSON sensor readings that look like this:

```json
{
  "device_id": "HYDROLOGIC-Device-001",
  "timestamp": "2024-01-15T10:30:00Z",
  "readings": {
    "pressure_upstream": 60.5,
    "flow_rate": 51.2,
    "gate_a_position": 45.0
  }
}
```

The values will vary each time you run the generator because they include random variation. Pressure values stay near 60 PSI, flow rates near 50 gallons per minute, and gate positions between 0 and 100 percent.

## Code Overview

The notebook starts with Python basics: creating variables, working with dictionaries, and using `print()` to display output. It then introduces the `json` module, which converts Python dictionaries into JSON strings — the standard format for sending data between IoT devices and servers.

The middle section builds a sensor reading dictionary step by step. You'll add a device ID, generate an ISO 8601 timestamp with the `datetime` module, and create nested readings using `random.uniform()` to simulate real sensor noise.

The final section wraps everything into a `generate_reading()` function that returns a complete sensor data packet each time you call it. You'll use a loop to generate multiple readings and see how the values change with each call.

## Common Issues

- **Notebook won't upload:** Make sure you are signed into your Google account. If the upload button does not respond, try a different browser (Chrome works best with Colab).
- **Cells produce errors when run out of order:** Colab cells depend on earlier cells. If you get a `NameError` (variable not defined), click **Runtime > Restart runtime**, then run every cell from the top in sequence.
- **`ModuleNotFoundError` for `json` or `random`:** These are built-in Python modules and should work without installation. If you see this error, restart the runtime — it usually means the Python environment is in a bad state.

## Resources

- [Google Colab Getting Started](https://colab.research.google.com/notebooks/intro.ipynb) — interactive tutorial on using Colab notebooks
- [Python JSON Module](https://docs.python.org/3/library/json.html) — official documentation for reading and writing JSON
- [Python datetime Module](https://docs.python.org/3/library/datetime.html) — working with dates, times, and ISO 8601 formatting
