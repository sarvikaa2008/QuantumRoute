\# QuantumRoute — Emergency Route Optimization



\## Smarter Route Planning for Emergency Vehicles



\### Project Overview



QuantumRoute is a web-based emergency route-planning project designed to help plan routes for ambulances and fire engines. It compares alternative driving routes, estimates travel time, screens mapped road information, and helps identify suitable hospitals based on configured medical facility information.



The project aims to make emergency route planning more organized by presenting important route details through a single interactive website.



\### Problem Statement



During emergencies, reaching the incident location quickly and identifying a suitable hospital are important challenges. Comparing alternative routes and checking road restrictions can be difficult when information is spread across different sources.



QuantumRoute aims to simplify this process by bringing route comparison, estimated travel information, and hospital facility details together in one platform.



\### Proposed Solution



QuantumRoute uses mapping services and a route-ranking approach to compare available driving routes and identify a preferred option based on estimated planning time, distance, and approximate road-screening results.



The system supports two emergency workflows:



\* Ambulance: Plans the journey from the ambulance's starting location to the patient, followed by a route from the patient to a suitable configured hospital.

\* Fire Engine: Plans the journey from a configured fire station to the fire incident location.



\### Key Features



\* Two Emergency Vehicle Modes: Separate workflows for ambulances and fire engines.

\* Location Input: Supports manually entered locations and GPS coordinates.

\* Alternative Route Comparison: Retrieves alternative driving routes when available.

\* Estimated Travel Information: Displays route distance and estimated planning time.

\* Hospital Selection: Compares configured hospitals according to medical facility profiles and route estimates.

\* Road Screening: Checks sampled route points against mapped road information to identify possible restrictions.

\* Route Ranking: Ranks routes using estimated planning time, distance, road-class penalties, and possible restriction warnings.

\* Interactive Map: Displays routes and locations through an interactive map interface.



\### System Workflow



\#### Ambulance Workflow



1\. Enter or obtain the ambulance's starting location.

2\. Enter or obtain the patient's location.

3\. Retrieve and compare alternative routes to the patient.

4\. Select a required medical facility, if needed.

5\. Compare configured hospitals using facility information and estimated routes.

6\. Display the preferred hospital and route details.



\#### Fire Engine Workflow



1\. Enter or obtain the fire incident location.

2\. Use the configured fire station as the starting point.

3\. Retrieve alternative driving routes.

4\. Screen mapped road information for possible restrictions.

5\. Rank the routes and display the preferred option.



\### Technologies Used



\* Python — Route-planning logic and scoring.

\* Flask — Backend framework and API.

\* HTML — Website structure.

\* CSS — Website styling and layout.

\* JavaScript — User interactions and map functionality.

\* Leaflet — Interactive map display.

\* OpenStreetMap — Map and road information.

\* OSRM — Driving-route retrieval.

\* Nominatim — Location search and geocoding.

\* Overpass API — Retrieval of mapped road information for screening.



\### Route Ranking Approach



QuantumRoute ranks routes using a combination of:



\* Estimated planning time.

\* Route distance.

\* Approximate road-class penalties.

\* Possible mapped road-restriction warnings.



This approach helps compare available routes using several factors rather than distance alone.



\### Installation and Setup



\#### Prerequisites



\* Python installed on your computer.

\* Visual Studio Code or another code editor.

\* Internet connection to access the mapping services.



\#### Step 1: Open the Project



Open the QuantumRoute project folder in Visual Studio Code.



\#### Step 2: Install Dependencies



Open the terminal in the project folder and run:



```

py -m pip install -r requirements.txt

```



\#### Step 3: Run the Application



Execute:



```

py app.py

```



\#### Step 4: Open the Website



Open your browser and visit:



http://127.0.0.1:5000



Keep the terminal running while using the application.



\### Project Impact



QuantumRoute aims to support more organized emergency route planning by bringing route comparison, estimated travel information, possible road restrictions, and configured hospital facility details into one interactive platform.



The project also provides an opportunity to explore how route optimization, mapping technologies, and future quantum-computing techniques could contribute to emergency transportation research.



\### Future Enhancements



\* Integration of verified real-time traffic information.

\* Live emergency vehicle tracking.

\* Integration with verified hospital availability information.

\* Improved road accessibility and vehicle restriction checks.

\* Exploration of quantum-computing algorithms for route optimization.



\### Conclusion



QuantumRoute demonstrates a technology-based approach to emergency route planning by combining interactive mapping, alternative driving routes, route scoring, road screening, and hospital facility comparison.



The project aims to make emergency route planning more organized and provides a foundation for exploring intelligent emergency transportation systems and future quantum-computing techniques.



