"""
Unity Formatter
===============
Converts a list of Route objects into the JSON format consumed by Unity C#.

Minimal output (what Unity reads from stdout)
---------------------------------------------
    {"items": ["Bus21A", "Bus7", "BusX5"]}

Rich output (for debugging; Unity ignores extra keys)
-----------------------------------------------------
    {
        "items": ["Bus21A", "Bus7"],
        "debug": {
            "total_time_min":    34.5,
            "num_transfers":     1,
            "total_walk_m":      120.0,
            "reliability_score": 0.94,
            "cost":              56.2,
            "all_routes": [
                {"buses": ["Bus21A","Bus7"], "time_min": 34.5, "transfers": 1},
                {"buses": ["BusX5"],         "time_min": 41.0, "transfers": 0}
            ]
        }
    }

Unity C# integration example
----------------------------
    using System.Diagnostics;
    using Newtonsoft.Json;

    var p = new Process();
    p.StartInfo.FileName  = "python";
    p.StartInfo.Arguments = "main.py --origin A --dest D";
    p.StartInfo.RedirectStandardOutput = true;
    p.Start();
    string json  = p.StandardOutput.ReadToEnd();
    var   result = JsonConvert.DeserializeObject<RouteResult>(json);
    // result.items == ["Bus21A", "Bus7"]
"""

import json
import sys
from typing import List, Dict, Any, TYPE_CHECKING

if TYPE_CHECKING:
    from routing.raptor_router import Route


class UnityFormatter:
    """
    Formats routing results as Unity-compatible JSON.

    Parameters
    ----------
    bus_prefix     : prefix prepended to raw route IDs (default "Bus")
    include_debug  : include extra debug payload alongside "items"
    """

    def __init__(self, bus_prefix: str = "Bus", include_debug: bool = False):
        self.bus_prefix    = bus_prefix
        self.include_debug = include_debug

    # -----------------------------------------------------------------------
    # Primary output
    # -----------------------------------------------------------------------

    def to_json(self, routes: List["Route"]) -> str:
        """
        Return minimal Unity JSON.

        The "items" list represents the buses to take, in order, on the
        single best route found.  Example: ["Bus21A", "Bus7"]
        """
        items   = self._best_items(routes)
        payload: Dict[str, Any] = {"items": items}

        if self.include_debug and routes:
            payload["debug"] = self._debug_payload(routes)

        return json.dumps(payload)

    # -----------------------------------------------------------------------
    # Internal helpers
    # -----------------------------------------------------------------------

    def _best_items(self, routes: List["Route"]) -> List[str]:
        if not routes:
            return []
        return [self._fmt(rid) for rid in routes[0].bus_ids()]

    def _fmt(self, route_id: str) -> str:
        """
        Normalise a route ID for Unity.
        "21A"   → "Bus21A"
        "Bus7"  → "Bus7"   (already prefixed)
        "WALK"  → "WALK"   (kept as-is)
        """
        if not route_id or route_id in ("WALK", ""):
            return route_id
        p = self.bus_prefix
        if route_id.upper().startswith(p.upper()):
            return p + route_id[len(p):]    # re-prefix with canonical casing
        return p + route_id

    def _debug_payload(self, routes: List["Route"]) -> Dict[str, Any]:
        best = routes[0]
        rel  = 1.0 - min(best.reliability_cost, 1.0)
        return {
            "total_time_min":    round(best.total_time_min,  1),
            "num_transfers":     best.num_transfers,
            "total_walk_m":      round(best.total_walk_m,    0),
            "reliability_score": round(rel,                   2),
            "cost":              round(best.cost,             2),
            "all_routes": [
                {
                    "buses":     [self._fmt(b) for b in r.bus_ids()],
                    "time_min":  round(r.total_time_min, 1),
                    "transfers": r.num_transfers,
                    "walk_m":    round(r.total_walk_m, 0),
                    "cost":      round(r.cost, 2),
                }
                for r in routes
            ],
        }
