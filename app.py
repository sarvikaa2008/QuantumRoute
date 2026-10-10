from flask import Flask, render_template, request, jsonify
import math
import re
import requests

app = Flask(__name__)

# ==================================================
# QUANTUMROUTE CONFIGURATION
# ==================================================

DESTINATIONS = {
    "PSG Hospitals, Coimbatore": {
        "type": "Hospital",
        "coordinates": None,
    },
    "Coimbatore Medical College Hospital": {
        "type": "Hospital",
        "coordinates": None,
    },
    "Ganga Hospital, Coimbatore": {
        "type": "Hospital",
        "coordinates": None,
    },
    "Coimbatore Fire Station - Gopalapuram Area": {
        "type": "Fire Station",
        # Approximate coordinates: longitude, latitude.
        # Verify the station location before demonstration.
        "coordinates": [76.9683566, 10.9978005],
    },
}

FIRE_STATION_NAME = (
    "Coimbatore Fire Station - Gopalapuram Area"
)

HEADERS = {
    "User-Agent": "QuantumRoute-Student-Project/1.0"
}

# Demonstration assumptions, not live traffic data.
PLANNING_SPEED_KMH = 25
EXTRA_BUFFER_MINUTES = 2
DISTANCE_WEIGHT = 0.35

VEHICLE_PROFILES = {
    "ambulance": {
        "label": "Ambulance",
        "width_m": 2.5,
        "height_m": 3.0,
        "local_road_weight": 1.5,
    },
    "fire_engine": {
        "label": "Fire Engine",
        "width_m": 2.6,
        "height_m": 3.5,
        "local_road_weight": 2.5,
    },
}

LOCAL_ROAD_CLASSES = {
    "service",
    "living_street",
    "track",
}

LOWER_ORDER_ROADS = {
    "service",
    "living_street",
    "track",
    "residential",
    "unclassified",
}

OVERPASS_URL = "https://overpass-api.de/api/interpreter"

FACILITY_LABELS = {
    "general_emergency": "General Emergency Care",
    "trauma_care": "Trauma Care",
    "cardiac_care": "Cardiac Care",
}

# Static demonstration profiles.
# Verify these details with the actual hospitals.
HOSPITAL_PROFILES = {
    "PSG Hospitals, Coimbatore": {
        "facilities": {
            "general_emergency",
            "trauma_care",
            "cardiac_care",
        },
    },
    "Coimbatore Medical College Hospital": {
        "facilities": {
            "general_emergency",
            "trauma_care",
            "cardiac_care",
        },
    },
    "Ganga Hospital, Coimbatore": {
        "facilities": {
            "general_emergency",
            "trauma_care",
        },
    },
}


# ==================================================
# LOCATION HANDLING
# ==================================================

def geocode_place(place):
    """Convert a manually entered place into coordinates."""

    response = requests.get(
        "https://nominatim.openstreetmap.org/search",
        params={
            "q": place,
            "format": "jsonv2",
            "limit": 1,
            "countrycodes": "in",
        },
        headers=HEADERS,
        timeout=20,
    )

    response.raise_for_status()
    results = response.json()

    if not results:
        return None

    return [
        float(results[0]["lon"]),
        float(results[0]["lat"]),
    ]


def get_location_coordinates(location_name=None, coordinates=None):
    """
    Obtain coordinates from GPS or manual entry.

    Coordinate format: [longitude, latitude].
    Manual locations are restricted to the Coimbatore project area.
    """

    if coordinates is not None:
        if not isinstance(coordinates, (list, tuple)):
            return None

        if len(coordinates) != 2:
            return None

        try:
            longitude = float(coordinates[0])
            latitude = float(coordinates[1])

            if not (
                math.isfinite(longitude)
                and math.isfinite(latitude)
            ):
                return None

            if not (-180 <= longitude <= 180):
                return None

            if not (-90 <= latitude <= 90):
                return None

            # Restrict this project prototype to Coimbatore.
            if not (
                76.70 <= longitude <= 77.15
                and 10.85 <= latitude <= 11.25
            ):
                return None

            return [longitude, latitude]

        except (TypeError, ValueError):
            return None

    if not location_name:
        return None

    query = str(location_name).strip()

    if not query:
        return None

    return geocode_place(
        query + ", Coimbatore, Tamil Nadu, India"
    )


# ==================================================
# TRAVEL-TIME ESTIMATION
# ==================================================

def calculate_planning_time(distance_km, map_time_min):
    """
    Estimate planning time using the larger of the routing
    service estimate and the demonstration speed estimate.
    """

    distance_based_time = (
        distance_km / PLANNING_SPEED_KMH * 60
    ) + EXTRA_BUFFER_MINUTES

    return math.ceil(
        max(map_time_min, distance_based_time)
    )


# ==================================================
# RETRIEVE ALTERNATIVE DRIVING ROUTES
# ==================================================

def get_raw_routes(start_coordinates, destination_coordinates):
    """Retrieve available alternative driving routes from OSRM."""

    url = (
        "https://router.project-osrm.org/route/v1/driving/"
        f"{start_coordinates[0]},{start_coordinates[1]};"
        f"{destination_coordinates[0]},{destination_coordinates[1]}"
    )

    response = requests.get(
        url,
        params={
            "overview": "full",
            "geometries": "geojson",
            "alternatives": 3,
            "steps": "false",
        },
        headers=HEADERS,
        timeout=30,
    )

    response.raise_for_status()
    data = response.json()

    if data.get("code") != "Ok" or not data.get("routes"):
        return []

    routes = []

    for route in data["routes"]:
        distance_km = route["distance"] / 1000
        map_time_min = route["duration"] / 60

        routes.append({
            "distance_km": round(distance_km, 2),
            "duration_min": round(map_time_min, 1),
            "planning_time_min": calculate_planning_time(
                distance_km,
                map_time_min,
            ),
            "geometry": route["geometry"],
        })

    return routes


# ==================================================
# OPENSTREETMAP ROAD SCREENING
# ==================================================

def sample_geometry(coordinates, max_points=5):
    """Select representative points along a route."""

    if not coordinates:
        return []

    if len(coordinates) <= max_points:
        return coordinates

    indexes = sorted({
        round(
            i * (len(coordinates) - 1) / (max_points - 1)
        )
        for i in range(max_points)
    })

    return [
        coordinates[index]
        for index in indexes
    ]


def parse_dimension_m(value):
    """Parse common road-width and height tag formats."""

    if value is None:
        return None

    text = str(value).strip().lower()
    match = re.search(r"(\d+(?:\.\d+)?)", text)

    if not match:
        return None

    number = float(match.group(1))

    if "mm" in text:
        return number / 1000

    if "cm" in text:
        return number / 100

    if "ft" in text or "feet" in text or "'" in text:
        return number * 0.3048

    return number


def point_segment_distance_m(point, first, second):
    """Approximate point-to-road-segment distance in metres."""

    lon, lat = point
    cos_lat = math.cos(math.radians(lat))

    ax = (first[0] - lon) * 111320 * cos_lat
    ay = (first[1] - lat) * 110540

    bx = (second[0] - lon) * 111320 * cos_lat
    by = (second[1] - lat) * 110540

    dx = bx - ax
    dy = by - ay

    denominator = dx * dx + dy * dy

    if denominator == 0:
        return math.hypot(ax, ay)

    t = max(
        0.0,
        min(
            1.0,
            -(ax * dx + ay * dy) / denominator,
        ),
    )

    return math.hypot(
        ax + t * dx,
        ay + t * dy,
    )


def point_to_way_distance_m(point, geometry):
    """Find the approximate distance from a point to a mapped road."""

    if not geometry:
        return float("inf")

    if len(geometry) == 1:
        return point_segment_distance_m(
            point,
            geometry[0],
            geometry[0],
        )

    return min(
        point_segment_distance_m(
            point,
            geometry[index],
            geometry[index + 1],
        )
        for index in range(len(geometry) - 1)
    )


def get_restriction_flags(tags, vehicle_type):
    """Identify possible restrictions from mapped road tags."""

    flags = []

    for key in ("access", "vehicle", "emergency"):
        value = str(tags.get(key, "")).lower()

        if value in {"no", "private"}:
            flags.append(f"{key}={value}")

    if vehicle_type == "fire_engine":
        hgv_value = str(tags.get("hgv", "")).lower()

        if hgv_value in {"no", "private"}:
            flags.append(
                f"hgv={hgv_value}; applicability must be verified"
            )

    vehicle = VEHICLE_PROFILES[vehicle_type]

    for key, vehicle_size in (
        ("maxwidth", vehicle["width_m"]),
        ("maxheight", vehicle["height_m"]),
    ):
        if key not in tags:
            continue

        road_limit = parse_dimension_m(tags[key])

        if road_limit is None:
            flags.append(
                f"Could not interpret {key}={tags[key]}"
            )

        elif road_limit < vehicle_size:
            flags.append(
                f"{key}={tags[key]} may be below "
                "the configured vehicle dimensions"
            )

    return flags


def screen_routes_with_osm(
    routes,
    vehicle_type,
    avoid_local_roads,
):
    """Screen sampled route points against nearby mapped roads."""

    if not routes:
        return

    points_by_route = [
        sample_geometry(
            route.get("geometry", {}).get("coordinates", [])
        )
        for route in routes
    ]

    unique_points = {}

    for points in points_by_route:
        for lon, lat in points:
            unique_points[(round(lon, 5), round(lat, 5))] = (
                lon,
                lat,
            )

    if not unique_points:
        for route in routes:
            route.update({
                "osm_screening_available": False,
                "road_types_found": [],
                "local_road_samples": None,
                "restriction_flags": [],
                "potential_restriction": False,
                "suitability_label":
                    "Unverified — route geometry unavailable",
                "suitability_penalty": 0.0,
            })

        return

    query_parts = []

    for lon, lat in unique_points.values():
        query_parts.append(
            f"way(around:15,{lat:.6f},{lon:.6f})[highway];"
        )

    query = (
        "[out:json][timeout:15];("
        + "".join(query_parts)
        + ");out tags geom;"
    )

    try:
        response = requests.post(
            OVERPASS_URL,
            data={"data": query},
            headers=HEADERS,
            timeout=22,
        )

        response.raise_for_status()
        data = response.json()

        ways = [
            item
            for item in data.get("elements", [])
            if (
                item.get("type") == "way"
                and item.get("geometry")
                and item.get("tags", {}).get("highway")
            )
        ]

    except (requests.RequestException, ValueError):
        app.logger.warning(
            "OpenStreetMap road screening unavailable."
        )

        for route in routes:
            route.update({
                "osm_screening_available": False,
                "road_types_found": [],
                "local_road_samples": None,
                "restriction_flags": [],
                "potential_restriction": False,
                "suitability_label":
                    "Unverified — road screening unavailable",
                "suitability_penalty": 0.0,
            })

        return

    prepared_ways = []

    for way in ways:
        tags = way.get("tags", {})

        geometry = [
            (node["lon"], node["lat"])
            for node in way["geometry"]
            if "lon" in node and "lat" in node
        ]

        if geometry:
            prepared_ways.append((tags, geometry))

    profile = VEHICLE_PROFILES[vehicle_type]

    for route, sample_points in zip(routes, points_by_route):
        road_types = set()
        local_road_samples = 0
        flags = set()

        for point in sample_points:
            closest_distance = float("inf")
            closest_tags = None

            for tags, geometry in prepared_ways:
                distance = point_to_way_distance_m(
                    point,
                    geometry,
                )

                if distance < closest_distance:
                    closest_distance = distance
                    closest_tags = tags

            if closest_tags is None or closest_distance > 12:
                continue

            road_type = str(
                closest_tags.get("highway", "unknown")
            )

            road_types.add(road_type)

            if (
                road_type in LOCAL_ROAD_CLASSES
                or (
                    avoid_local_roads
                    and road_type in LOWER_ORDER_ROADS
                )
            ):
                local_road_samples += 1

            for flag in get_restriction_flags(
                closest_tags,
                vehicle_type,
            ):
                flags.add(flag)

        multiplier = profile["local_road_weight"]

        if avoid_local_roads:
            multiplier *= 1.8

        route_flags = sorted(flags)

        route.update({
            "osm_screening_available": True,
            "road_types_found": sorted(road_types),
            "local_road_samples": local_road_samples,
            "restriction_flags": route_flags,
            "potential_restriction": bool(route_flags),
            "suitability_label": (
                "Possible restriction flagged — verify"
                if route_flags
                else (
                    "No restriction tag found; "
                    "suitability remains unverified"
                )
            ),
            "suitability_penalty": round(
                local_road_samples * multiplier,
                2,
            ),
        })


# ==================================================
# ROUTE SCORING
# ==================================================

def score_routes(routes, vehicle_type, avoid_local_roads):
    """Rank routes using time, distance and road screening."""

    screen_routes_with_osm(
        routes,
        vehicle_type,
        avoid_local_roads,
    )

    for route in routes:
        base_score = (
            route["planning_time_min"]
            + DISTANCE_WEIGHT * route["distance_km"]
        )

        restriction_penalty = (
            10000
            if route.get("potential_restriction")
            else 0
        )

        route["base_score"] = round(base_score, 2)

        route["score"] = round(
            base_score
            + route.get("suitability_penalty", 0)
            + restriction_penalty,
            2,
        )

    routes.sort(
        key=lambda route: (
            bool(route.get("potential_restriction")),
            route["score"],
            route["planning_time_min"],
            route["distance_km"],
        )
    )

    for number, route in enumerate(routes, start=1):
        route["route_number"] = number

    return routes


# ==================================================
# HOSPITAL HELPERS
# ==================================================

def facility_matches(hospital_name, required_facility):
    """Check the configured hospital facility profile."""

    if required_facility == "any":
        return True

    profile = HOSPITAL_PROFILES.get(
        hospital_name,
        {},
    )

    return required_facility in profile.get(
        "facilities",
        set(),
    )


def public_facility_list(hospital_name):
    """Return readable facility names."""

    facilities = HOSPITAL_PROFILES.get(
        hospital_name,
        {},
    ).get("facilities", set())

    return [
        FACILITY_LABELS[key]
        for key in sorted(facilities)
        if key in FACILITY_LABELS
    ]


def find_best_hospital(
    patient_coordinates,
    required_facility,
    vehicle_type,
    avoid_local_roads,
):
    """
    Compare configured hospitals using their best-ranked
    route from the patient's location.
    """

    candidates = []

    for hospital_name, info in DESTINATIONS.items():

        if info["type"] != "Hospital":
            continue

        if not facility_matches(
            hospital_name,
            required_facility,
        ):
            continue

        try:
            hospital_coordinates = info["coordinates"]

            if hospital_coordinates is None:
                hospital_coordinates = geocode_place(
                    hospital_name
                    + ", Coimbatore, Tamil Nadu, India"
                )

            if not hospital_coordinates:
                continue

            routes = get_raw_routes(
                patient_coordinates,
                hospital_coordinates,
            )

            if not routes:
                continue

            routes = score_routes(
                routes,
                vehicle_type,
                avoid_local_roads,
            )

            routes.sort(
                key=lambda route: (
                    bool(route.get("potential_restriction")),
                    route["score"],
                    route["planning_time_min"],
                    route["distance_km"],
                )
            )

            best_route = routes[0]

            candidates.append({
                "name": hospital_name,
                "coordinates": hospital_coordinates,
                "distance_km": best_route["distance_km"],
                "planning_time_min":
                    best_route["planning_time_min"],
                "score": best_route["score"],
                "has_warning":
                    best_route.get(
                        "potential_restriction",
                        False,
                    ),
                "facilities": public_facility_list(
                    hospital_name
                ),
                "routes": routes,
            })

        except requests.RequestException:
            app.logger.warning(
                "Could not retrieve routes to %s",
                hospital_name,
            )

    if not candidates:
        return None

    candidates.sort(
        key=lambda candidate: (
            candidate["has_warning"],
            candidate["score"],
        )
    )

    return candidates[0], candidates


# ==================================================
# HOME PAGE
# ==================================================

@app.route("/")
def home():
    return render_template(
        "index.html",
        destinations=DESTINATIONS,
    )


# ==================================================
# ROUTE PLANNING API
# ==================================================

@app.route("/api/plan", methods=["POST"])
def plan_route():

    data = request.get_json(silent=True) or {}

    vehicle_type = str(
        data.get("vehicle_type", "ambulance")
    ).strip()

    incident_location = str(
        data.get("incident_location", "")
    ).strip()

    incident_coordinates_input = data.get(
        "incident_coordinates"
    )

    avoid_local_roads = (
        data.get("avoid_local_roads", False) is True
    )

    required_facility = str(
        data.get("required_facility", "any")
    ).strip()

    if vehicle_type not in VEHICLE_PROFILES:
        return jsonify({
            "error": "Please select a valid emergency vehicle."
        }), 400

    if (
        not incident_location
        and incident_coordinates_input is None
    ):
        return jsonify({
            "error": "Please provide the incident location."
        }), 400

    valid_facilities = {
        "any",
        *FACILITY_LABELS.keys(),
    }

    if required_facility not in valid_facilities:
        return jsonify({
            "error": "Please select a valid medical facility."
        }), 400

    try:
        # ------------------------------------------
        # OBTAIN INCIDENT / PATIENT LOCATION
        # ------------------------------------------

        incident_coordinates = get_location_coordinates(
            incident_location,
            incident_coordinates_input,
        )

        if not incident_coordinates:
            return jsonify({
                "error": (
                    "Incident location not found. Check the location "
                    "or GPS coordinates. Locations must be in Coimbatore."
                )
            }), 404

        # ==========================================
        # FIRE ENGINE WORKFLOW
        # ==========================================

        if vehicle_type == "fire_engine":

            fire_station_coordinates = (
                DESTINATIONS[FIRE_STATION_NAME]["coordinates"]
            )

            if not fire_station_coordinates:
                return jsonify({
                    "error": (
                        "The configured fire station has no coordinates."
                    )
                }), 500

            routes = get_raw_routes(
                fire_station_coordinates,
                incident_coordinates,
            )

            if not routes:
                return jsonify({
                    "error": (
                        "No driving routes were found from the "
                        "configured fire station to the incident."
                    )
                }), 502

            routes = score_routes(
                routes,
                "fire_engine",
                avoid_local_roads,
            )

            for number, route in enumerate(routes, start=1):
                route["route_number"] = number

            best_route = routes[0]

            return jsonify({
                "vehicle_type": "fire_engine",
                "vehicle_label": "Fire Engine",
                "workflow": "fire_station_to_incident",

                "start": FIRE_STATION_NAME,
                "start_coordinates": fire_station_coordinates,

                "destination": (
                    incident_location or "Fire Incident GPS Location"
                ),
                "destination_type": "Fire Incident",
                "destination_coordinates": incident_coordinates,

                "routes": routes,
                "best_route": best_route,

                "hospital_candidates": [],

                "scoring_method": (
                    "Planning-time estimate + weighted distance "
                    "+ mapped road-class penalty + possible "
                    "restriction warning penalty."
                ),

                "note": (
                    "The fire engine starts from the configured fire "
                    "station. The incident location can be entered "
                    "manually or obtained using GPS. Map estimates are "
                    "not live traffic predictions. Road screening is "
                    "approximate and cannot confirm route safety. "
                    "Verify the configured fire station before use."
                ),
            })

        # ==========================================
        # AMBULANCE WORKFLOW
        # ==========================================

        start_location = str(
            data.get("start", "")
        ).strip()

        start_coordinates_input = data.get(
            "start_coordinates"
        )

        if (
            not start_location
            and start_coordinates_input is None
        ):
            return jsonify({
                "error": (
                    "Please provide the ambulance's starting location."
                )
            }), 400

        start_coordinates = get_location_coordinates(
            start_location,
            start_coordinates_input,
        )

        if not start_coordinates:
            return jsonify({
                "error": (
                    "Ambulance starting location not found. "
                    "Check the location or GPS coordinates."
                )
            }), 404

        # ------------------------------------------
        # STAGE 1: AMBULANCE TO PATIENT
        # ------------------------------------------

        patient_routes = get_raw_routes(
            start_coordinates,
            incident_coordinates,
        )

        if not patient_routes:
            return jsonify({
                "error": (
                    "No driving routes were found from the "
                    "ambulance to the patient."
                )
            }), 502

        patient_routes = score_routes(
            patient_routes,
            "ambulance",
            avoid_local_roads,
        )

        for number, route in enumerate(
            patient_routes,
            start=1,
        ):
            route["route_number"] = number

        best_patient_route = patient_routes[0]

        # ------------------------------------------
        # STAGE 2: PATIENT TO SUITABLE HOSPITAL
        # ------------------------------------------

        hospital_result = find_best_hospital(
            incident_coordinates,
            required_facility,
            "ambulance",
            avoid_local_roads,
        )

        if hospital_result is None:
            return jsonify({
                "error": (
                    "No routes were found to configured hospitals "
                    "matching the selected facility. Try another "
                    "facility or verify the hospital configuration."
                )
            }), 502

        chosen_hospital, hospital_candidates = hospital_result

        hospital_routes = chosen_hospital["routes"]

        for number, route in enumerate(
            hospital_routes,
            start=1,
        ):
            route["route_number"] = number

        best_hospital_route = hospital_routes[0]

        # ------------------------------------------
        # RETURN AMBULANCE RESULTS
        # ------------------------------------------

        return jsonify({
            "vehicle_type": "ambulance",
            "vehicle_label": "Ambulance",
            "workflow": "ambulance_to_patient_then_hospital",

            "start": start_location or "Ambulance GPS Location",
            "start_coordinates": start_coordinates,

            "patient_location": (
                incident_location or "Patient GPS Location"
            ),
            "patient_coordinates": incident_coordinates,

            "destination": chosen_hospital["name"],
            "destination_type": "Hospital",
            "destination_coordinates":
                chosen_hospital["coordinates"],

            "required_facility": required_facility,
            "required_facility_label": FACILITY_LABELS.get(
                required_facility,
                "No specific facility preference",
            ),

            "patient_routes": patient_routes,
            "best_patient_route": best_patient_route,

            "hospital_routes": hospital_routes,
            "best_hospital_route": best_hospital_route,

            "hospital_candidates": [
                {
                    "name": candidate["name"],
                    "distance_km": candidate["distance_km"],
                    "planning_time_min":
                        candidate["planning_time_min"],
                    "score": candidate["score"],
                    "facilities": candidate["facilities"],
                    "has_warning": candidate["has_warning"],
                }
                for candidate in hospital_candidates
            ],

            "scoring_method": (
                "Routes are ranked using estimated planning time, "
                "distance, mapped road-class penalties and possible "
                "restriction warnings."
            ),

            "note": (
                "The ambulance journey contains two stages: "
                "ambulance to patient, then patient to the selected "
                "hospital. Estimates are not live traffic predictions. "
                "Hospital profiles are static and do not confirm "
                "capacity, availability or patient acceptance. "
                "Road screening is approximate and cannot establish "
                "that a route is safe."
            ),
        })

    except requests.Timeout:
        return jsonify({
            "error": (
                "A map service took too long to respond. Please try again."
            )
        }), 504

    except requests.RequestException:
        app.logger.exception("Map service request failed")

        return jsonify({
            "error": (
                "Could not connect to a map service. "
                "Check your internet connection and try again."
            )
        }), 502

    except (TypeError, ValueError, KeyError):
        app.logger.exception("Unexpected route-planning data")

        return jsonify({
            "error": (
                "Unexpected route-planning data was received. "
                "Please try again."
            )
        }), 502


# ==================================================
# RUN APPLICATION
# ==================================================

if __name__ == "__main__":
    app.run(debug=True)