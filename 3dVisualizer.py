from panda3d.core import loadPrcFileData

loadPrcFileData("", "window-type cocoa")
loadPrcFileData("", "gl-version 2 1")
loadPrcFileData("", "framebuffer-srgb false")
loadPrcFileData("", "multisamples 0")
loadPrcFileData("", "framebuffer-multisample 0")
loadPrcFileData("", "prefer-parasite-buffer #f")

from ursina import *
import math, json, os, sys

# ── Load config ────────────────────────────────────────────────────────────────
CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "hospital_config.json")

with open(CONFIG_PATH) as f:
    CONFIG = json.load(f)

FLOOR_NAMES = list(CONFIG["floors"].keys())   # ordered list
FLOOR_COUNT = len(FLOOR_NAMES)

# Map ordinal number → floor name  (0 = Ground, 1 = First, …)
ORDINAL_MAP = {i: name for i, name in enumerate(FLOOR_NAMES)}

def floor_index_from_arg():
    """Parse an optional CLI arg like  python hospital_viewer.py 3  (→ floor index 3)."""
    if len(sys.argv) > 1:
        try:
            idx = int(sys.argv[1])
            if 0 <= idx < FLOOR_COUNT:
                return idx
        except ValueError:
            pass
    else:
        idx = int(input("Enter floor index: "))
        return idx

# ── App ────────────────────────────────────────────────────────────────────────
app = Ursina(title="Hospital Navigation System", borderless=False)
window.fps_counter.enabled = True
window.color = color.hex("#0b0f18")

# ── Lighting ───────────────────────────────────────────────────────────────────
DirectionalLight(direction=Vec3(0.6, -1, -0.4), color=color.rgba(255, 255, 255, 180))
AmbientLight(color=color.rgba(150, 160, 180, 255))
PointLight(color=color.rgba(120, 160, 255, 120), position=(20, 40, 20))

# ── Zone palette ───────────────────────────────────────────────────────────────
NEUTRAL = color.rgba(38, 42, 55, 160)

ZONE_COLOR = {
    "Public":      NEUTRAL,
    "Circulation": NEUTRAL,
    "Critical":    color.rgba(255, 70,  70,  70),
    "Utility":     color.rgba(255, 170, 60,  50),
    "Staff":       color.rgba(60,  220, 150, 50),
    "Clinical":    color.rgba(80,  140, 255, 50),
    "Diagnostic":  color.rgba(200, 120, 255, 50),
}

WALL_H = 3.2

# ── State ──────────────────────────────────────────────────────────────────────
current_floor_idx = [floor_index_from_arg()]
scene_entities   = []   # all entities we spawn per floor (so we can wipe them)

# ── Camera rig ─────────────────────────────────────────────────────────────────
cam = {"yaw": -45, "pitch": 60, "dist": 85, "drag": False, "last": Vec2(0, 0)}

def apply_camera(pivot):
    yaw   = math.radians(cam["yaw"])
    pitch = math.radians(cam["pitch"])
    x = math.sin(yaw)   * math.cos(pitch) * cam["dist"]
    y = math.sin(pitch) * cam["dist"]
    z = math.cos(yaw)   * math.cos(pitch) * cam["dist"]
    camera.position = pivot + Vec3(x, y, z)
    camera.look_at(pivot)

# ── Beacon ─────────────────────────────────────────────────────────────────────
beacon = Entity(model='sphere', color=color.hex("#22c55e"), scale=0.9,
                position=(0, 0.8, 0))
glow   = Entity(model='sphere', color=color.hex("#22c55e"),
                scale=2.2, alpha=0.15, parent=beacon)

beacon_state = {"node": 0, "t": 0.0, "path": [], "speed": 6}

# ── Floor builder ──────────────────────────────────────────────────────────────
pivot_pos = [Vec3(20, 0, 35)]   # updated per floor

def clear_floor():
    for e in scene_entities:
        destroy(e)
    scene_entities.clear()

def load_floor(floor_idx):
    clear_floor()

    floor_name = ORDINAL_MAP[floor_idx]
    floor_data = CONFIG["floors"][floor_name]
    slots      = floor_data["slots"]

    # bounding box → centre pivot
    min_x = min(s[0]        for s in slots)
    max_x = max(s[0] + s[2] for s in slots)
    min_z = min(s[1]        for s in slots)
    max_z = max(s[1] + s[3] for s in slots)

    world_cx = (min_x + max_x) / 2
    world_cz = (min_z + max_z) / 2
    pivot_pos[0] = Vec3(world_cx, 0, world_cz)

    world_w = (max_x - min_x) + 16
    world_d = (max_z - min_z) + 16

    # ground plane
    g = Entity(model='plane', scale=(world_w, 1, world_d),
               position=(world_cx, 0.0, world_cz),
               color=color.rgba(20, 25, 40, 255))
    scene_entities.append(g)


    grid = Entity(model='grid', scale=120, color=color.rgba(60, 70, 90, 40),
                  position=pivot_pos[0])
    scene_entities.append(grid)

    # outer perimeter walls
    margin = 8
    for sx, sz, sw, sd, scol in [
        (world_cx, min_z - margin,  world_w,     0.5,  color.rgba(80,90,110,90)),
        (world_cx, max_z + margin,  world_w,     0.5,  color.rgba(80,90,110,90)),
        (min_x - margin, world_cz,  0.5, world_d+16, color.rgba(80,90,110,90)),
        (max_x + margin, world_cz,  0.5, world_d+16, color.rgba(80,90,110,90)),
    ]:
        e = Entity(model='cube',
                   scale=(sw, WALL_H, sd),
                   position=(sx, WALL_H/2, sz),
                   color=scol)
        scene_entities.append(e)

    # rooms
    for x, z, w, d, label, zone, fixed, sid in slots:
        if zone == "Circulation":
            continue

        cx = x + w / 2
        cz = z + d / 2

        base = color.rgba(200, 70, 70, 80) if fixed else ZONE_COLOR.get(zone, NEUTRAL)

        room = Entity(model='cube',
                      position=(cx, WALL_H/2, cz),
                      scale=(w, WALL_H, d),
                      color=base,
                      double_sided=True)
        scene_entities.append(room)

        lbl = Text(text=f"[{sid}] {label}",
                   parent=room,
                   position=(0, WALL_H + 0.25, 0),
                   scale=2.0,
                   color=color.rgba(240, 245, 255, 240),
                   origin=(0, 0),
                   billboard=True,
                   always_on_top=True)
        scene_entities.append(lbl)

    # path (stub — same path for all floors; replace with real routing later)
    path = [(6, 8), (6, 20), (18, 20), (18, 8)]
    beacon_state["path"] = path
    beacon_state["node"] = 0

    if path:
        beacon.position = Vec3(path[0][0], 0.8, path[0][1])

    for i in range(len(path) - 1):
        a, b = path[i], path[i+1]
        mx, mz = (a[0]+b[0])/2, (a[1]+b[1])/2
        length  = math.dist(a, b)
        angle   = math.degrees(math.atan2(b[0]-a[0], b[1]-a[1]))
        seg = Entity(model='cube',
                     position=(mx, 0.05, mz),
                     scale=(0.2, 0.05, length),
                     rotation_y=angle,
                     color=color.rgba(34, 197, 94, 200))
        scene_entities.append(seg)

    apply_camera(pivot_pos[0])
    update_floor_hud(floor_name, floor_data)

# ── HUD ────────────────────────────────────────────────────────────────────────
legend_items = [
    ("Critical",   "#ff4646"),
    ("Utility",    "#ffaa28"),
    ("Staff",      "#3cdc96"),
    ("Clinical",   "#5090ff"),
    ("Diagnostic", "#c878ff"),
    ("Locked",     "#c83232"),
    ("Route",      "#22c55e"),
]
for i, (name, hx) in enumerate(legend_items):
    Text(text=f"■  {name}", position=(-0.87, 0.46 - i*0.055),
         scale=1.0, color=color.hex(hx), origin=(-0.5, 0), parent=camera.ui)

ctrl_hint = Text(text="↑↓ change floor   RMB orbit   Scroll zoom   R reset",
                 position=(0, -0.47), scale=0.85,
                 color=color.rgba(160,170,190,160),
                 origin=(0, 0), parent=camera.ui)

floor_label = Text(text="", position=(0, 0.46), scale=1.3,
                   color=color.rgba(220,230,255,230),
                   origin=(0, 0), parent=camera.ui)

floor_comment = Text(text="", position=(0, 0.41), scale=0.85,
                     color=color.rgba(150,160,180,180),
                     origin=(0, 0), parent=camera.ui)

def update_floor_hud(floor_name, floor_data):
    floor_label.text  = f"FL {current_floor_idx[0]}  ·  {floor_name.upper()}"
    floor_comment.text = floor_data.get("comment", "")

# ── Initial load ───────────────────────────────────────────────────────────────
load_floor(current_floor_idx[0])

# ── Input ──────────────────────────────────────────────────────────────────────
def input(key):
    if key == "scroll up":
        cam["dist"] = max(20, cam["dist"] - 5)
    if key == "scroll down":
        cam["dist"] = min(200, cam["dist"] + 5)
    if key == "right mouse down":
        cam["drag"] = True
        cam["last"] = Vec2(mouse.x, mouse.y)
    if key == "right mouse up":
        cam["drag"] = False
    if key == "r":
        cam["yaw"], cam["pitch"], cam["dist"] = -45, 60, 85

    # Floor switching
    if key in ("up arrow", "page up"):
        idx = min(current_floor_idx[0] + 1, FLOOR_COUNT - 1)
        if idx != current_floor_idx[0]:
            current_floor_idx[0] = idx
            load_floor(idx)

    if key in ("down arrow", "page down"):
        idx = max(current_floor_idx[0] - 1, 0)
        if idx != current_floor_idx[0]:
            current_floor_idx[0] = idx
            load_floor(idx)

    # Direct floor number: press 0-9 (+ shift for 10-19)
    for digit in range(10):
        if key == str(digit):
            target = digit if digit < FLOOR_COUNT else current_floor_idx[0]
            if target != current_floor_idx[0]:
                current_floor_idx[0] = target
                load_floor(target)

# ── Update loop ────────────────────────────────────────────────────────────────
def update():
    dt = time.dt
    beacon_state["t"] += dt

    if cam["drag"]:
        d = Vec2(mouse.x, mouse.y) - cam["last"]
        cam["last"] = Vec2(mouse.x, mouse.y)
        cam["yaw"]   -= d.x * 120
        cam["pitch"]  = clamp(cam["pitch"] + d.y * 90, 10, 85)

    apply_camera(pivot_pos[0])

    path = beacon_state["path"]
    i    = beacon_state["node"]

    if not path or i >= len(path):
        beacon_state["node"] = 0
        return

    tx, tz = path[i]
    target  = Vec3(tx, 0.8, tz)
    d       = target - beacon.position
    dist    = d.length()
    step    = dt * beacon_state["speed"]

    if dist <= step:
        beacon.position = target
        beacon_state["node"] += 1
    else:
        d.normalize()
        beacon.position += d * step

    glow.scale = 1.8 + math.sin(beacon_state["t"] * 8) * 0.4

app.run()