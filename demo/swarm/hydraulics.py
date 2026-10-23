"""Plausible, consistent water hydraulics for one HYDROLOGIC unit.

HYDROLOGIC manages *flow* with two gates (0-90 degrees); it does not reduce
pressure in normal operation. Downstream pressure falls only when the gates are
forced far more closed than the product ever would, starving the building. That
is the physical effect the demo's coordinated scenario produces.
"""

import math


def opening(gate_a, gate_b):
    """Effective flow opening (0-1): the mean of each gate's sine."""
    return (math.sin(math.radians(gate_a)) + math.sin(math.radians(gate_b))) / 2.0


def downstream_psi(upstream, flow_lpm, gate_a, gate_b):
    """Downstream pressure after the gates, in psi.

    Loss grows with the square of flow per unit opening, so clamping the gates
    while demand continues pulls downstream pressure down fast.
    """
    op = opening(gate_a, gate_b)
    if op <= 0:
        return 0.0
    loss = 2.0 * (flow_lpm / (op * 100.0)) ** 2
    return max(0.0, upstream - loss)


def demand_lpm(building_idx, t_s, phase):
    """Smooth water demand for a building, between 60 and 180 LPM.

    A 30-minute period with a per-building phase keeps the fleet from moving in
    lockstep on its own, which is what makes a real coordinated change stand out.
    """
    val = 120.0 + 60.0 * math.sin(2.0 * math.pi * t_s / 1800.0 + phase)
    return max(60.0, min(180.0, val))
