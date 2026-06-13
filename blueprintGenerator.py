import matplotlib.pyplot as plt
import matplotlib.patches as patches
import math
import random
import copy
import json
import os


def get_coordinates_dict(slots):
    coords = {}
    for slot in slots:
        # Safety check to skip arbitrary comments or invalid formatting
        if not isinstance(slot, (list, tuple)) or len(slot) < 7:
            continue

        # Unpack based on available elements (supporting both 7 and 8 value schemas)
        if len(slot) == 8:
            x, y, w, h, label, category, is_circulation, room_number = slot
            # Combine Room Number and Label for display purposes
            display_label = f"[{room_number}] {label}"
        else:
            x, y, w, h, label, category, is_circulation = slot
            display_label = label

        # Store using the display_label so your visualization layer renders it
        coords[display_label] = {
            "x": x,
            "y": y,
            "w": w,
            "h": h,
            "category": category,
            "is_circulation": is_circulation
        }
    return coords


def calculate_layout_distance(slots, critical_links):
    coords = get_coordinates_dict(slots)
    total_score = 0
    for r1, r2 in critical_links:
        if r1 in coords and r2 in coords:
            total_score += math.dist(coords[r1], coords[r2])
        else:
            total_score += 1000
    return total_score


def generate_dynamic_report(floor_name, original_slots, optimized_slots, orig_dist, opt_dist):
    print("\n" + "=" * 95)
    print(f"               DYNAMIC ARCHITECTURAL ADVANTAGE AUDIT: {floor_name.upper()}               ")
    print("=" * 95)
    print(f"[*] Original Path Distance : {orig_dist:.2f} meters")
    print(f"[*] Optimized Path Distance: {opt_dist:.2f} meters")
    efficiency = ((orig_dist - opt_dist) / orig_dist * 100) if orig_dist > 0 else 0
    print(f"[*] Operational Efficiency  : +{efficiency:.1f}% reduction in transit latency")
    print("-" * 95)
    print(f"{'Functional Unit':<24} | {'Size':<10} | {'Status / Dynamic Reason'}")
    print("-" * 95)

    orig_coords = get_coordinates_dict(original_slots)
    opt_coords = get_coordinates_dict(optimized_slots)

    for orig_s in original_slots:
        label = orig_s[4]
        clean_name = label.replace('\n', ' ')
        opt_s = next(s for s in optimized_slots if s[4] == label)
        size_str = f"{orig_s[2]}x{orig_s[3]}"

        if orig_s[6]:
            print(f"{clean_name:<24} | {size_str:<10} | STATIONARY: Locked circulation backbone channel.")
        elif orig_s[0] == opt_s[0] and orig_s[1] == opt_s[1]:
            print(f"{clean_name:<24} | {size_str:<10} | STATIONARY: Maintained baseline coordinate equilibrium.")
        else:
            print(f"{clean_name:<24} | {size_str:<10} | ADAPTED: Re-allocated to satisfy critical link proximity.")
    print("=" * 95 + "\n")


def draw_blueprint(slots, output_directory, filename, title_text):
    """Draws and exports blueprints directly into targeted subfolders."""
    fig, ax = plt.subplots(figsize=(10, 15), dpi=150)
    bg_color, wall_color, text_color, room_bg, corridor_bg = "#0f172a", "#38bdf8", "#f8fafc", "#1e293b", "#0f172a"

    fig.patch.set_facecolor(bg_color)
    ax.set_facecolor(bg_color)
    ax.set_xlim(-5, 47)
    ax.set_ylim(-5, 77)
    ax.axis('off')

    # Draw structural bounds
    ax.add_patch(
        patches.Rectangle((-4, -4), 50, 80, linewidth=1.5, edgecolor=wall_color, facecolor="none", linestyle='--'))
    ax.add_patch(patches.Rectangle((0, 0), 42, 72, linewidth=3, edgecolor=wall_color, facecolor="none"))

    for slot in slots:
        # Dynamic unpacking to handle both old 7-value and new 8-value schema
        if len(slot) == 8:
            x, y, w, h, label, zone, is_fixed, room_number = slot
            display_label = f"{room_number}\n{label}"  # Newline for readability
        else:
            x, y, w, h, label, zone, is_fixed = slot
            display_label = label

        face_color = corridor_bg if zone == "Circulation" else room_bg
        style = ":" if is_fixed else "-"
        lw = 3 if is_fixed else 2

        ax.add_patch(
            patches.Rectangle((x, y), w, h, linewidth=lw, linestyle=style, edgecolor=wall_color, facecolor=face_color,
                              zorder=2))

        # Use display_label here instead of original label
        ax.text(x + w / 2, y + h / 2, display_label, color=text_color, weight="bold", fontsize=6, ha="center",
                va="center",
                zorder=3)

    ax.text(21, -2.5, title_text.upper(), color="#f87171", weight="bold", fontsize=14, ha="center", va="center",
            zorder=4)
    plt.tight_layout()

    # Safe multi-platform path generation
    full_output_path = os.path.join(output_directory, filename)
    plt.savefig(full_output_path, bbox_inches='tight', facecolor=fig.get_facecolor())
    plt.close()
    print(f"[✔] Blueprint saved: {full_output_path}")


def run_multi_floor_optimization(config_path="hospital_config.json", tolerance=0.25):
    if not os.path.exists(config_path):
        print(f"Error: Configuration file '{config_path}' not found.")
        return

    # Dynamic environment checks & initialization of export folders
    orig_dir = "original"
    opt_dir = "optimized"
    os.makedirs(orig_dir, exist_ok=True)
    os.makedirs(opt_dir, exist_ok=True)

    with open(config_path, "r") as f:
        config_data = json.load(f)

    print(f"\nProcessing Facility Model: {config_data.get('hospital_name', 'Unnamed Project')}")

    def area(slot):
        return slot[2] * slot[3]

    def can_swap(s1, s2):
        return (abs(area(s1) - area(s2)) / max(area(s1), area(s2))) <= tolerance

    for floor_name, floor_data in config_data["floors"].items():
        print(f"\nParsing configurations for: {floor_name}...")

        slots = floor_data["slots"]
        critical_links = floor_data["critical_links"]

        original_slots = copy.deepcopy(slots)
        orig_dist = calculate_layout_distance(original_slots, critical_links)

        shufflable_indices = [i for i, s in enumerate(slots) if not s[6]]
        best_slots = copy.deepcopy(slots)
        best_dist = orig_dist

        for _ in range(4000):
            test_slots = copy.deepcopy(best_slots)
            idx1, idx2 = random.sample(shufflable_indices, 2)

            if not can_swap(test_slots[idx1], test_slots[idx2]):
                continue

            test_slots[idx1][4], test_slots[idx2][4] = test_slots[idx2][4], test_slots[idx1][4]
            test_slots[idx1][5], test_slots[idx2][5] = test_slots[idx2][5], test_slots[idx1][5]

            test_dist = calculate_layout_distance(test_slots, critical_links)
            if test_dist < best_dist:
                best_dist = test_dist
                best_slots = test_slots

        generate_dynamic_report(floor_name, original_slots, best_slots, orig_dist, best_dist)

        # File naming serialization
        clean_floor_name = floor_name.lower().replace(" ", "_") + ".png"

        # Isolation rendering calls targeting specific directories
        draw_blueprint(original_slots, orig_dir, clean_floor_name, f"{floor_name} (Original)")
        draw_blueprint(best_slots, opt_dir, clean_floor_name, f"{floor_name} (Optimized)")


if __name__ == "__main__":
    print("\n=== Directory-Isolated Multi-Floor Optimizer ===\n")
    try:
        tolerance_input = float(input("Enter swap size tolerance threshold (default 0.25): ").strip())
    except ValueError:
        tolerance_input = 0.25

    run_multi_floor_optimization(tolerance=max(0.05, min(tolerance_input, 0.8)))