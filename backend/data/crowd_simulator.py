import time
import random

def get_crowd_status():
    """
    Simulates real-time density and trends for Zone A, Zone B, Zone C, and Zone D.
    Uses a 10-minute (600-second) cycle to represent a full match progression
    (Pre-match, 1st half, Halftime, 2nd half, Post-match) so the demo remains dynamic.
    Adds slight random noise (+/- 2%) on each call to simulate real-time movement.
    """
    cycle_duration = 600.0
    now = time.time()
    elapsed = now % cycle_duration

    # Determine simulated match phase
    if elapsed < 120:
        # Pre-match (0 to 120s): fans arriving
        phase = "Pre-Match (Gate Entry)"
        time_desc = "30 mins to Kickoff"
        base_densities = {
            "Zone A": (72.0, "UP"),
            "Zone B": (68.0, "UP"),
            "Zone C": (55.0, "UP"),
            "Zone D": (48.0, "STABLE")
        }
    elif elapsed < 240:
        # 1st half (120 to 240s): fans in seats
        phase = "First Half (Match in Progress)"
        time_desc = "35th Minute"
        base_densities = {
            "Zone A": (92.0, "STABLE"),
            "Zone B": (89.0, "STABLE"),
            "Zone C": (84.0, "STABLE"),
            "Zone D": (81.0, "STABLE")
        }
    elif elapsed < 360:
        # Halftime (240 to 360s): concourse spike for food & restrooms
        phase = "Halftime (Concourse Spike)"
        time_desc = "Halftime"
        base_densities = {
            "Zone A": (96.0, "UP"),
            "Zone B": (94.0, "UP"),
            "Zone C": (91.0, "UP"),
            "Zone D": (87.0, "STABLE")
        }
    elif elapsed < 480:
        # 2nd half (360 to 480s): fans back in seats
        phase = "Second Half (Match in Progress)"
        time_desc = "75th Minute"
        base_densities = {
            "Zone A": (94.0, "STABLE"),
            "Zone B": (91.0, "STABLE"),
            "Zone C": (87.0, "STABLE"),
            "Zone D": (82.0, "STABLE")
        }
    else:
        # Post-match (480 to 600s): egress
        phase = "Post-Match (Egress / Exiting)"
        time_desc = "Match Ended"
        base_densities = {
            "Zone A": (64.0, "DOWN"),
            "Zone B": (52.0, "DOWN"),
            "Zone C": (47.0, "DOWN"),
            "Zone D": (38.0, "DOWN")
        }

    # Add random fluctuation to make it feel "live" when polling
    zones_data = []
    for zone_name, (base_val, trend) in base_densities.items():
        noise = random.uniform(-2.0, 2.0)
        final_val = max(5.0, min(100.0, base_val + noise))
        zones_data.append({
            "zone_name": zone_name,
            "capacity_pct": round(final_val, 1),
            "trend": trend
        })

    return {
        "zones": zones_data,
        "match_phase": phase,
        "simulated_time": time_desc,
        "timestamp": round(now, 2)
    }
