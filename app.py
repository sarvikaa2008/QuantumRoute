
from flask import Flask, render_template, request, jsonify
import requests

app = Flask(__name__)

# Demo hospital information; availability is simulated.
HOSPITALS = {
    "PSG Hospitals, Coimbatore": {
        "rating": 5, "available": True
    },
    "Coimbatore Medical College Hospital": {
        "rating": 5, "available": True
    },
    "Ganga Hospital, Coimbatore": {
        "rating": 4, "available": False
    }
}

HEADERS = {"User-Agent": "QuantumRouteStudentPrototype/1.0"}


def geocode(place):
    response = requests.get(
        "https://nominatim.openstreetmap.org/search",
        params={"q": place + ", Coimbatore, Tamil Nadu, India",
                "format": "json", "limit": 1},
        headers=HEADERS,
        timeout=15
    )
    response.raise_for_status()
    results = response.json()

    if not results:
        raise ValueError(f"Could not find: {place}")

    return float(results[0]["lon"]), float(results[0]["lat"])


@app.route("/")
def home():
    return render_template("index.html", hospitals=HOSPITALS)


@app.route("/api/plan", methods=["POST"])
def plan():
    data = request.get_json(silent=True) or {}

    start = str(data.get("start", "")).strip()
    destination = str(data.get("destination", "")).strip()
    emergency = data.get("emergency", "High")
    traffic = data.get("traffic") == "yes"
    blocked = data.get("blocked") == "yes"

    if not start or destination not in HOSPITALS:
        return jsonify(error="Enter a starting location and choose a hospital."), 400

    if emergency not in ["Critical", "High", "Normal"]:
        emergency = "High"

    hospital = HOSPITALS[destination]

    try:
        start_lon, start_lat = geocode(start)
        end_lon, end_lat = geocode(destination)

        url = (
            "https://router.project-osrm.org/route/v1/driving/"
            f"{start_lon},{start_lat};{end_lon},{end_lat}"
        )
        response = requests.get(
            url,
            params={"overview": "full", "geometries": "geojson",
                    "alternatives": "true", "steps": "false"},
            timeout=20
        )
        response.raise_for_status()
        payload = response.json()

        routes = payload.get("routes", [])
        if not routes:
            return jsonify(error="No drivable route was found."), 404

        # Demonstration penalty factors, not live traffic measurements.
        # The route with the lowest adjusted cost is recommended.
        scored = []
        for route in routes:
            duration = route["duration"] / 60
            distance = route["distance"] / 1000
            cost = duration

            if traffic:
                cost *= 1.5
            if blocked and len(routes) > 1:
                # Simulates a closure by penalizing the first candidate.
                if route is routes[0]:
                    cost *= 2.5

            scored.append({
                "route": route,
                "minutes": round(duration, 1),
                "km": round(distance, 2),
                "cost": cost
            })

        scored.sort(key=lambda item: item["cost"])
        chosen = scored[0]

        reason = (
            "Selected the route with the lowest adjusted travel-time score. "
            "Traffic and road-closure effects are simulated."
        )
        if emergency == "Critical":
            reason += " Critical emergency: prioritize a quick response."
        elif emergency == "High":
            reason += " High priority: minimize estimated journey time."
        else:
            reason += " Normal priority: compare available routes."

        if not hospital["available"]:
            reason += (
                " WARNING: this hospital is marked unavailable in demo data. "
                "Choose another hospital for the demonstration."
            )

        return jsonify({
            "start": start,
            "destination": destination,
            "emergency": emergency,
            "hospital_available_demo": hospital["available"],
            "routes_found": len(routes),
            "minutes": chosen["minutes"],
            "km": chosen["km"],
            "geometry": chosen["route"]["geometry"],
            "reason": reason,
            "method": "Route alternatives + simulated decision scoring",
            "data_note": (
                "Map roads and estimated route come from OpenStreetMap/OSRM. "
                "Traffic, closures and hospital availability are simulated. "
                "No live ambulance GPS is used."
            )
        })

    except requests.RequestException:
        return jsonify(
            error="The map service could not be reached. Check your internet and try again."
        ), 502
    except (ValueError, KeyError, TypeError):
        return jsonify(
            error="Could not plan this route. Try a more specific Coimbatore location."
        ), 400


if __name__ == "__main__":
    app.run(debug=True)