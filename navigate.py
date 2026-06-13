import json
import math
import heapq
from collections import defaultdict


class HospitalNavigator:
    def __init__(self, json_path):
        with open(json_path, "r") as f:
            self.data = json.load(f)

        self.floors = self.data["floors"]
        self.graph = defaultdict(list)
        self.node = {}  # (floor, room) -> info

        self._build()

    # -----------------------------
    # geometry helpers
    # -----------------------------
    def dist(self, a, b):
        return math.dist(a, b)

    def direction(self, a, b):
        ax, ay = a
        bx, by = b

        dx = bx - ax
        dy = by - ay

        # dominant axis decides instruction
        if abs(dx) > abs(dy):
            if dx > 0:
                return "Move RIGHT"
            else:
                return "Move LEFT"
        else:
            if dy > 0:
                return "Move FORWARD"
            else:
                return "Move BACKWARD"

    def detailed_direction(self, a, b):
        ax, ay = a
        bx, by = b

        dx = bx - ax
        dy = by - ay

        # angle-based classification (more stable than axis dominance)
        angle = math.degrees(math.atan2(dy, dx))

        if -30 <= angle <= 30:
            return "directly to your RIGHT"
        elif 30 < angle <= 75:
            return "ahead and slightly to your RIGHT"
        elif 75 < angle <= 105:
            return "directly ahead"
        elif 105 < angle <= 150:
            return "ahead and slightly to your LEFT"
        elif -75 <= angle < -30:
            return "behind and to your RIGHT"
        elif -105 <= angle < -75:
            return "directly behind"
        elif -150 <= angle < -105:
            return "behind and to your LEFT"
        else:
            return "directly to your LEFT"

    # -----------------------------
    # build graph
    # -----------------------------
    def _build(self):
        floor_nodes = {}

        for floor, data in self.floors.items():
            floor_nodes[floor] = []

            for s in data["slots"]:
                x, y, w, h, label, zone, fixed, room = s

                nid = (floor, room)
                center = (x + w / 2, y + h / 2)

                self.node[nid] = {
                    "pos": center,
                    "label": label,
                    "floor": floor,
                    "room": room
                }

                floor_nodes[floor].append(nid)

        # intra-floor links
        for floor, nodes in floor_nodes.items():
            for i in range(len(nodes)):
                for j in range(i + 1, len(nodes)):
                    a, b = nodes[i], nodes[j]

                    pa = self.node[a]["pos"]
                    pb = self.node[b]["pos"]

                    d = self.dist(pa, pb)

                    self.graph[a].append((b, d))
                    self.graph[b].append((a, d))

        self._connect_elevators(floor_nodes)

    # -----------------------------
    # SINGLE LIFT / STAIR PORTAL LOGIC
    # -----------------------------
    def _connect_elevators(self, floor_nodes):
        floors = list(self.floors.keys())

        for keyword in ["LIFT", "STAIRS"]:
            portals = []

            for f in floors:
                for n in floor_nodes[f]:
                    if keyword in self.node[n]["label"].upper():
                        portals.append(n)

            # IMPORTANT: chain into ONE logical vertical system
            for i in range(len(portals) - 1):
                a, b = portals[i], portals[i + 1]

                # cheap vertical jump cost
                self.graph[a].append((b, 1))
                self.graph[b].append((a, 1))

    # -----------------------------
    # find node by room number
    # -----------------------------
    def get(self, room):
        for k in self.node:
            if k[1] == room:
                return k
        return None

    # -----------------------------
    # DIJKSTRA
    # -----------------------------
    def route(self, start_room, end_room):
        start = self.get(start_room)
        end = self.get(end_room)

        pq = [(0, start, [])]
        seen = set()

        while pq:
            cost, node, path = heapq.heappop(pq)

            if node in seen:
                continue
            seen.add(node)

            path = path + [node]

            if node == end:
                return path

            for nxt, w in self.graph[node]:
                if nxt not in seen:
                    heapq.heappush(pq, (cost + w, nxt, path))

        return None

    # -----------------------------
    # HUMAN NAVIGATION OUTPUT
    # -----------------------------
    def explain(self, path):
        if not path:
            return []

        steps = []

        def pos(n):
            return self.node[n]["pos"]

        def label(n):
            return self.node[n]["label"].upper()

        start = path[0]
        end = path[-1]

        # ----------------------------
        # 1. INITIAL ORIENTATION
        # ----------------------------
        steps.append(
            f"Start at Room {start[1]} on {start[0]}. "
            f"Orient yourself facing the main corridor."
        )

        # ----------------------------
        # 2. LOCAL MOVEMENT (same floor until lift)
        # ----------------------------
        current_floor = start[0]
        lift_used = False
        target_floor = end[0]

        i = 0
        while i < len(path) - 1:
            a = path[i]
            b = path[i + 1]

            fa, ra = a
            fb, rb = b

            # ----------------------------
            # FLOOR CHANGE → SINGLE LIFT EVENT
            # ----------------------------
            if fa != fb and not lift_used:
                steps.append(
                    f"Proceed straight through corridor. "
                    f"You will see the LIFT area ahead."
                )

                steps.append(
                    f"Take the LIFT once and travel directly from "
                    f"{fa} → {target_floor}. Doors will open at your destination floor."
                )

                lift_used = True
                i += 1
                continue

            # skip intermediate vertical nodes after lift
            if fa != fb:
                i += 1
                continue

            # ----------------------------
            # SAME FLOOR NAVIGATION
            # ----------------------------
            pa = pos(a)
            pb = pos(b)

            dx = pb[0] - pa[0]
            dy = pb[1] - pa[1]

            instruction = None

            if abs(dx) > abs(dy):
                if dx > 0:
                    instruction = "Move RIGHT along the corridor"
                else:
                    instruction = "Move LEFT along the corridor"
            else:
                if dy > 0:
                    instruction = "Continue FORWARD"
                else:
                    instruction = "Move BACKWARD slightly"

            # visual perception layer
            steps.append(instruction)
            steps.append(
                f"You will see Room {rb} ahead on Floor {fa}. "
                f"Use it as a visual landmark while continuing."
            )

            i += 1

        # ----------------------------
        # 3. FINAL APPROACH (ENHANCED VISIBILITY)
        # ----------------------------

        pa = pos(path[-2])
        pb = pos(end)

        dx = pb[0] - pa[0]
        dy = pb[1] - pa[1]

        d = self.dist(pa, pb)

        if d > 20:
            visibility = "at a distance across the corridor"
        elif d > 10:
            visibility = "clearly visible ahead"
        else:
            visibility = "right in front of you"

        direction_hint = self.detailed_direction(pa, pb)

        steps.append(
            f"As you approach the final junction, Room {end[1]} is {visibility}, "
            f"positioned {direction_hint}."
        )

        steps.append(
            f"Destination reached: Room {end[1]} on {end[0]}"
        )

        return steps

    def get_path_with_positions(self, path):
        result = []

        for node in path:
            floor, room = node
            info = self.node[node]

            result.append({
                "floor": floor,
                "room": room,
                "label": info["label"],
                "x": info["pos"][0],
                "y": info["pos"][1]
            })

        return result

# -----------------------------
# RUN
# -----------------------------
if __name__ == "__main__":
    nav = HospitalNavigator("hospital_config.json")

    start = input("Start room number: ")
    end = input("End room number: ")

    path = nav.route(start, end)

    if path:
        print("\nNAVIGATION GUIDE:\n")
        for s in nav.explain(path):
            print("-", s)
    else:
        print("No route found")
