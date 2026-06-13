from flask import Flask, request, jsonify, render_template, send_from_directory
from navigate import HospitalNavigator
import os
app = Flask(__name__)

nav = HospitalNavigator("hospital_config.json")


# -----------------------------
# UI ENTRY
# -----------------------------
BLUEPRINT_DIR = os.path.abspath("./original")  # adjust path here
@app.route("/blueprints/<path:filename>")
def blueprints(filename):
    full_path = os.path.join(BLUEPRINT_DIR, filename)
    print("Requested:", full_path)
    return send_from_directory(BLUEPRINT_DIR, filename)
@app.route("/")
def home():
    return render_template("index.html")


# -----------------------------
# ROUTE API (text + visual data)
# -----------------------------
@app.route("/route", methods=["POST"])
def route():
    data = request.get_json(force=True)

    start = data.get("start")
    end = data.get("end")

    if not start or not end:
        return jsonify({"error": "start and end are required"}), 400

    path = nav.route(start, end)

    if not path:
        return jsonify({"error": "No route found"}), 404

    return jsonify({
        "source": start,
        "destination": end,

        # human-readable navigation
        "steps": nav.explain(path),

        # structured data for blueprint rendering
        "path": nav.get_path_with_positions(path)
    })


# -----------------------------
# RUN SERVER
# -----------------------------
if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=5050,
        debug=True
    )