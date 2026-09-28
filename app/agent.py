# ruff: noqa
# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import datetime
import json
import pathlib
from zoneinfo import ZoneInfo

from a2ui.basic_catalog.provider import BasicCatalog
from a2ui.schema.manager import A2uiSchemaManager
from google.adk.agents import Agent
from google.adk.agents.callback_context import CallbackContext
from google.adk.apps import App
from google.adk.code_executors import AgentEngineSandboxCodeExecutor
from google.adk.memory import VertexAiMemoryBankService
from google.adk.models import Gemini
from google.adk.tools import ToolContext
from google.adk.tools.preload_memory_tool import PreloadMemoryTool
from google.cloud import firestore
from google.genai import types

from .a2ui_utils import a2ui_callback

# HARDCODED GCP Project ID and GCS Bucket Name
PROJECT_ID = "qwiklabs-gcp-03-4e2380eb54ba"
BUCKET_NAME = "travel-concierge-qwiklabs-gcp-03-4e2380eb54ba"

_db_client = None

def get_firestore_client() -> firestore.Client:
    """Returns a singleton Firestore client instance using the hardcoded project ID."""
    global _db_client
    if _db_client is None:
        _db_client = firestore.Client(project=PROJECT_ID)
    return _db_client


def list_destinations(category: str = "") -> str:
    """Lists travel destinations from the Firestore database.

    Args:
        category: Optional category filter (e.g. 'Culture & Food', 'Romance & Art', 'Beach & Party', 'Nature & Adventure').

    Returns:
        JSON string containing the list of destinations.
    """
    db = get_firestore_client()
    docs = db.collection("destinations").stream()
    destinations = []
    for doc in docs:
        data = doc.to_dict()
        if category:
            cat = data.get("category", "")
            if category.lower() not in cat.lower():
                continue
        destinations.append(data)

    if not destinations:
        return json.dumps({"message": f"No destinations found matching category '{category}'." if category else "No destinations found."})

    return json.dumps(destinations, indent=2)


def get_destination_details(destination_id: str) -> str:
    """Retrieves full details for a specific travel destination from Firestore.

    Args:
        destination_id: The ID or name of the destination (e.g. 'tokyo', 'paris', 'kyoto', 'rio', 'reykjavik').

    Returns:
        JSON string with destination details or an error message if not found.
    """
    db = get_firestore_client()
    doc_ref = db.collection("destinations").document(destination_id.lower().strip())
    doc = doc_ref.get()

    if doc.exists:
        return json.dumps(doc.to_dict(), indent=2)

    # Fallback search by name if ID lookup fails
    docs = db.collection("destinations").stream()
    for d in docs:
        data = d.to_dict()
        if destination_id.lower().strip() in data.get("name", "").lower():
            return json.dumps(data, indent=2)

    return json.dumps({"error": f"Destination '{destination_id}' not found in database."})


def add_destination(
    destination_id: str,
    name: str,
    country: str,
    category: str,
    description: str,
    avg_daily_cost: int,
    top_attractions: str,
    best_season: str = "Year-round",
) -> str:
    """Adds a new destination or updates an existing destination in the Firestore database.

    Args:
        destination_id: Unique string identifier for the destination (e.g. 'rome', 'barcelona').
        name: Name of the destination city or region (e.g. 'Rome').
        country: Country where the destination is located (e.g. 'Italy').
        category: Category of travel (e.g. 'History & Culture', 'Beach & Leisure').
        description: A brief summary of what makes the destination attractive.
        avg_daily_cost: Estimated average daily cost in USD (integer).
        top_attractions: Comma-separated list of top attraction names.
        best_season: Best time of year to visit.

    Returns:
        Confirmation string with status.
    """
    db = get_firestore_client()
    clean_id = destination_id.lower().strip().replace(" ", "-")

    attractions_list = [a.strip() for a in top_attractions.split(",") if a.strip()]

    dest_data = {
        "id": clean_id,
        "name": name,
        "country": country,
        "category": category,
        "description": description,
        "avg_daily_cost": avg_daily_cost,
        "top_attractions": attractions_list,
        "best_season": best_season,
    }

    db.collection("destinations").document(clean_id).set(dest_data)
    return f"Successfully saved destination '{name}' ({clean_id}) to Firestore database."


def get_weather(query: str) -> str:
    """Simulates a web search. Use it get information on weather.

    Args:
        query: A string containing the location to get weather information for.

    Returns:
        A string with the simulated weather information for the queried location.
    """
    if "sf" in query.lower() or "san francisco" in query.lower():
        return "It's 60 degrees and foggy."
    elif "tokyo" in query.lower():
        return "It's 68 degrees and pleasant."
    elif "paris" in query.lower():
        return "It's 65 degrees and breezy."
    elif "kyoto" in query.lower():
        return "It's 70 degrees and sunny."
    elif "rio" in query.lower():
        return "It's 82 degrees and sunny."
    elif "reykjavik" in query.lower():
        return "It's 45 degrees and crisp."
    return "It's 75 degrees and sunny."


def get_current_time(query: str) -> str:
    """Simulates getting the current time for a city.

    Args:
        query: The name of the city to get the current time for.

    Returns:
        A string with the current time information.
    """
    if "sf" in query.lower() or "san francisco" in query.lower():
        tz_identifier = "America/Los_Angeles"
    elif "tokyo" in query.lower() or "kyoto" in query.lower():
        tz_identifier = "Asia/Tokyo"
    elif "paris" in query.lower():
        tz_identifier = "Europe/Paris"
    elif "rio" in query.lower():
        tz_identifier = "America/Sao_Paulo"
    elif "reykjavik" in query.lower():
        tz_identifier = "Atlantic/Reykjavik"
    else:
        return f"Sorry, I don't have timezone information for query: {query}."

    tz = ZoneInfo(tz_identifier)
    now = datetime.datetime.now(tz)
    return f"The current time for query {query} is {now.strftime('%Y-%m-%d %H:%M:%S %Z%z')}"


def calculate_trip_budget(
    destination_id: str,
    num_days: int = 3,
    num_travelers: int = 1,
    style_tier: str = "standard",
) -> str:
    """Calculates an itemized estimated trip budget for a destination.

    Args:
        destination_id: The ID or name of the destination (e.g. 'tokyo', 'paris', 'kyoto', 'rio', 'reykjavik', 'rome').
        num_days: Number of days for the trip (default: 3).
        num_travelers: Number of people traveling together (default: 1).
        style_tier: Travel style tier ('budget', 'standard', 'luxury'). Default is 'standard'.

    Returns:
        JSON string containing the detailed cost breakdown.
    """
    db = get_firestore_client()
    clean_id = destination_id.lower().strip()
    doc_ref = db.collection("destinations").document(clean_id)
    doc = doc_ref.get()

    dest_data = None
    if doc.exists:
        dest_data = doc.to_dict()
    else:
        # Fallback search by name
        docs = db.collection("destinations").stream()
        for d in docs:
            data = d.to_dict()
            if clean_id in data.get("name", "").lower():
                dest_data = data
                break

    if not dest_data:
        return json.dumps({"error": f"Destination '{destination_id}' not found in database to calculate budget."})

    base_daily_cost = float(dest_data.get("avg_daily_cost", 200))

    tier_multipliers = {
        "budget": 0.7,
        "standard": 1.0,
        "luxury": 1.8,
    }
    multiplier = tier_multipliers.get(style_tier.lower(), 1.0)
    adjusted_daily_cost = round(base_daily_cost * multiplier, 2)

    accommodation = round(adjusted_daily_cost * 0.45 * num_days * num_travelers, 2)
    food = round(adjusted_daily_cost * 0.30 * num_days * num_travelers, 2)
    activities = round(adjusted_daily_cost * 0.15 * num_days * num_travelers, 2)
    transport = round(adjusted_daily_cost * 0.10 * num_days * num_travelers, 2)
    total_cost = round(adjusted_daily_cost * num_days * num_travelers, 2)

    result = {
        "destination": dest_data.get("name"),
        "country": dest_data.get("country"),
        "num_days": num_days,
        "num_travelers": num_travelers,
        "style_tier": style_tier,
        "daily_cost_per_person": adjusted_daily_cost,
        "total_estimated_cost_usd": total_cost,
        "itemized_breakdown": {
            "accommodation": accommodation,
            "food_and_dining": food,
            "activities_and_sightseeing": activities,
            "local_transport": transport,
        },
    }
    return json.dumps(result, indent=2)


def search_attractions_by_interest(interest: str) -> str:
    """Searches top attractions across all destinations in Firestore that match a specific travel interest or keyword.

    Args:
        interest: Travel interest or activity keyword (e.g. 'temple', 'beach', 'museum', 'food', 'mountain', 'art', 'history').

    Returns:
        JSON string containing matching destinations and their relevant attractions.
    """
    db = get_firestore_client()
    docs = db.collection("destinations").stream()
    matches = []
    query_term = interest.lower().strip()

    for doc in docs:
        data = doc.to_dict()
        name = data.get("name")
        country = data.get("country")
        category = data.get("category", "")
        attractions = data.get("top_attractions", [])
        description = data.get("description", "")

        matching_attractions = [a for a in attractions if query_term in a.lower()]
        if query_term in category.lower() or query_term in description.lower() or matching_attractions:
            matches.append({
                "destination": name,
                "country": country,
                "category": category,
                "matching_attractions": matching_attractions if matching_attractions else attractions,
                "description": description,
            })

    if not matches:
        return json.dumps({"message": f"No attractions or destinations found matching interest '{interest}'."})

    return json.dumps(matches, indent=2)


def get_currency_exchange_rate(from_currency: str = "USD", to_currencies: str = "EUR,JPY,GBP,BRL") -> str:
    """Fetches real live currency exchange rates for travelers using the Frankfurter public API.

    Args:
        from_currency: The base currency code (e.g. 'USD', 'EUR', 'GBP'). Default is 'USD'.
        to_currencies: Comma-separated list of target currency codes (e.g. 'EUR,JPY,GBP,BRL').

    Returns:
        JSON string containing live exchange rates and date.
    """
    import os
    import urllib.request

    api_key = os.getenv("EXCHANGE_RATE_API_KEY", "")
    base = from_currency.upper().strip()
    targets = ",".join([c.strip().upper() for c in to_currencies.split(",") if c.strip()])

    url = f"https://api.frankfurter.app/latest?from={base}&to={targets}" if targets else f"https://api.frankfurter.app/latest?from={base}"

    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 TravelConcierge/1.0"})
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode())
            return json.dumps({
                "base_currency": data.get("base"),
                "date": data.get("date"),
                "rates": data.get("rates", {}),
            }, indent=2)
    except Exception as e:
        return json.dumps({"error": f"Failed to fetch exchange rates for {base}: {str(e)}"})


def get_maps_auth_headers() -> tuple[dict, str | None]:
    """Helper to return authentication headers for Google Maps / Places REST APIs."""
    import os
    import subprocess

    key = os.getenv("GOOGLE_MAPS_API_KEY", "")
    if key and key != "PASTE_KEY_HERE":
        return {"X-Goog-Api-Key": key}, key

    try:
        token = subprocess.check_output(["gcloud", "auth", "print-access-token"]).decode().strip()
        headers = {
            "Authorization": f"Bearer {token}",
            "X-Goog-User-Project": PROJECT_ID,
        }
        return headers, None
    except Exception:
        return {}, key if key else None


def geocode_address(address: str) -> str:
    """Uses the Google Maps Geocoding API to convert a location or address into coordinates and formatted address.

    Args:
        address: Address or landmark name (e.g. 'Tokyo Tower, Tokyo', '1600 Amphitheatre Pkwy, Mountain View, CA').

    Returns:
        JSON string containing name, formatted_address, and location coordinates (latitude, longitude).
    """
    import urllib.parse
    import urllib.request

    headers, key = get_maps_auth_headers()
    if key:
        url = f"https://maps.googleapis.com/maps/api/geocode/json?address={urllib.parse.quote(address)}&key={key}"
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=5) as resp:
                res = json.loads(resp.read().decode())
                if res.get("status") == "OK" and res.get("results"):
                    r = res["results"][0]
                    loc = r["geometry"]["location"]
                    return json.dumps({
                        "name": address,
                        "formatted_address": r.get("formatted_address"),
                        "location": {"latitude": loc.get("lat"), "longitude": loc.get("lng")},
                    }, indent=2)
        except Exception:
            pass

    # Places Text Search (New) REST API fallback
    url = "https://places.googleapis.com/v1/places:searchText"
    body = json.dumps({"textQuery": address}).encode("utf-8")
    req_headers = {
        "Content-Type": "application/json",
        "X-Goog-FieldMask": "places.displayName,places.formattedAddress,places.location",
    }
    req_headers.update(headers)
    req = urllib.request.Request(url, data=body, headers=req_headers)
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            res = json.loads(resp.read().decode())
            places = res.get("places", [])
            if places:
                p = places[0]
                return json.dumps({
                    "name": p.get("displayName", {}).get("text"),
                    "formatted_address": p.get("formattedAddress"),
                    "location": p.get("location"),
                }, indent=2)
    except Exception as e:
        return json.dumps({"error": f"Failed to geocode address '{address}': {str(e)}"})

    return json.dumps({"error": f"Address '{address}' not found."})


def find_nearby_places(
    latitude: float,
    longitude: float,
    place_type: str = "tourist_attraction",
    radius_meters: float = 1000.0,
) -> str:
    """Uses the Google Places API (New) REST endpoint to search for nearby places of a given type.

    Args:
        latitude: Center latitude coordinate.
        longitude: Center longitude coordinate.
        place_type: Type of place to search for (e.g. 'restaurant', 'tourist_attraction', 'cafe', 'museum', 'lodging'). Default is 'tourist_attraction'.
        radius_meters: Search radius in meters (default: 1000.0).

    Returns:
        JSON string containing a list of nearby places with name, formatted_address, and location coordinates.
    """
    import urllib.request

    headers, _ = get_maps_auth_headers()
    url = "https://places.googleapis.com/v1/places:searchNearby"
    body = json.dumps({
        "includedTypes": [place_type],
        "maxResultCount": 5,
        "locationRestriction": {
            "circle": {
                "center": {"latitude": latitude, "longitude": longitude},
                "radius": radius_meters,
            }
        },
    }).encode("utf-8")

    req_headers = {
        "Content-Type": "application/json",
        "X-Goog-FieldMask": "places.displayName,places.formattedAddress,places.location",
    }
    req_headers.update(headers)

    try:
        req = urllib.request.Request(url, data=body, headers=req_headers)
        with urllib.request.urlopen(req, timeout=5) as resp:
            res = json.loads(resp.read().decode())
            places = res.get("places", [])
            results = []
            for p in places:
                results.append({
                    "name": p.get("displayName", {}).get("text"),
                    "formatted_address": p.get("formattedAddress"),
                    "location": p.get("location"),
                })
            return json.dumps(results, indent=2)
    except Exception as e:
        return json.dumps({"error": f"Failed to search nearby places: {str(e)}"})


def generate_destination_image(prompt: str, tool_context: ToolContext = None) -> str:
    """Generates an image for a travel destination or landmark using gemini-3.1-flash-lite-image in the global region. Saves the image as an artifact and uploads it to Cloud Storage, returning its public URL.

    Args:
        prompt: Description or prompt for the travel image to generate (e.g. 'A vibrant postcard of Tokyo with cherry blossoms').
        tool_context: ToolContext automatically injected by ADK.

    Returns:
        JSON string containing the public Cloud Storage URL (https://storage.googleapis.com/<bucket>/<object>) and image status.
    """
    import uuid
    from google import genai
    from google.cloud import storage

    try:
        genai_client = genai.Client(vertexai=True, project=PROJECT_ID, location="global")
        gen_prompt = f"Generate a high-quality travel postcard photo of: {prompt}"
        resp = genai_client.models.generate_content(
            model="gemini-3.1-flash-lite-image",
            contents=gen_prompt,
        )

        image_bytes = None
        for part in resp.candidates[0].content.parts:
            if part.inline_data and part.inline_data.data:
                image_bytes = part.inline_data.data
                break

        if not image_bytes:
            return json.dumps({"error": "No image bytes generated."})

        filename = f"destination_{uuid.uuid4().hex[:8]}.jpg"

        # (1) Save artifact to Playground's Artifacts panel if tool_context is provided
        if tool_context:
            artifact_part = types.Part.from_bytes(data=image_bytes, mime_type="image/jpeg")
            tool_context.save_artifact(filename=filename, artifact=artifact_part)

        # (2) Upload image bytes directly to public Cloud Storage bucket
        storage_client = storage.Client(project=PROJECT_ID)
        bucket = storage_client.bucket(BUCKET_NAME)
        blob = bucket.blob(filename)
        blob.upload_from_string(image_bytes, content_type="image/jpeg")

        public_url = f"https://storage.googleapis.com/{BUCKET_NAME}/{filename}"
        return json.dumps({
            "status": "success",
            "prompt": prompt,
            "filename": filename,
            "public_url": public_url,
        }, indent=2)

    except Exception as e:
        return json.dumps({"error": f"Failed to generate image: {str(e)}"})


def generate_destination_video(prompt: str, tool_context: ToolContext = None) -> str:
    """Generates a short video for a travel destination using Google's Omni model (gemini-omni-flash-preview) in the global region. Saves the video with tool_context.save_artifact so it shows up in the Playground's Artifacts panel, uploads the video bytes to the public Cloud Storage bucket, and returns its public https URL (https://storage.googleapis.com/<bucket>/<object>).

    Args:
        prompt: Description or prompt for the travel video to generate (e.g. 'A scenic aerial clip of Paris at sunset').
        tool_context: ToolContext automatically injected by ADK.

    Returns:
        JSON string containing status, filename, and public_url (https://storage.googleapis.com/<bucket>/<object>).
    """
    import base64
    import uuid
    import requests
    import google.auth
    import google.auth.transport.requests
    from google.cloud import storage

    try:
        credentials, _ = google.auth.default(scopes=["https://www.googleapis.com/auth/cloud-platform"])
        auth_req = google.auth.transport.requests.Request()
        credentials.refresh(auth_req)
        token = credentials.token

        url = f"https://aiplatform.googleapis.com/v1beta1/projects/{PROJECT_ID}/locations/global/interactions"
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }

        body = {
            "model": "gemini-omni-flash-preview",
            "input": [
                {
                    "type": "text",
                    "text": f"A short scenic travel video of: {prompt}"
                }
            ]
        }

        resp = requests.post(url, headers=headers, json=body, timeout=120)
        if resp.status_code != 200:
            return json.dumps({"error": f"API error ({resp.status_code}): {resp.text[:300]}"})

        data = resp.json()
        video_bytes = None
        mime_type = "video/mp4"

        for step in data.get("steps", []):
            if "content" in step:
                for item in step["content"]:
                    if item.get("type") == "video" or "data" in item:
                        b64_str = item.get("data") or item.get("bytesBase64Encoded")
                        if b64_str:
                            video_bytes = base64.b64decode(b64_str)
                            mime_type = item.get("mime_type", "video/mp4")
                            break
            if video_bytes:
                break

        if not video_bytes:
            return json.dumps({"error": "No video bytes generated by gemini-omni-flash-preview."})

        ext = ".mp4" if "mp4" in mime_type else ".webm"
        filename = f"video_{uuid.uuid4().hex[:8]}{ext}"

        # (1) Save artifact to Playground's Artifacts panel if tool_context is provided
        if tool_context:
            artifact_part = types.Part.from_bytes(data=video_bytes, mime_type=mime_type)
            tool_context.save_artifact(filename=filename, artifact=artifact_part)

        # (2) Upload video bytes directly to public Cloud Storage bucket
        storage_client = storage.Client(project=PROJECT_ID)
        bucket = storage_client.bucket(BUCKET_NAME)
        blob = bucket.blob(filename)
        blob.upload_from_string(video_bytes, content_type=mime_type)

        public_url = f"https://storage.googleapis.com/{BUCKET_NAME}/{filename}"
        return json.dumps({
            "status": "success",
            "prompt": prompt,
            "filename": filename,
            "public_url": public_url,
        }, indent=2)

    except Exception as e:
        return json.dumps({"error": f"Failed to generate video: {str(e)}"})


# Load Agent Engine resource name from deployment_metadata.json if present
DEPLOYMENT_METADATA_FILE = pathlib.Path(__file__).parent.parent / "deployment_metadata.json"
REMOTE_AGENT_RUNTIME_ID = "projects/821199284850/locations/us-central1/reasoningEngines/1357267389896458240"

if DEPLOYMENT_METADATA_FILE.exists():
    try:
        with open(DEPLOYMENT_METADATA_FILE) as f:
            _meta = json.load(f)
            REMOTE_AGENT_RUNTIME_ID = _meta.get("remote_agent_runtime_id", REMOTE_AGENT_RUNTIME_ID)
    except Exception:
        pass

code_executor = AgentEngineSandboxCodeExecutor(
    agent_engine_resource_name=REMOTE_AGENT_RUNTIME_ID
)


# Memory Bank Instance ID
MEMORY_BANK_ID = "132288291251683328"


async def generate_memories_callback(callback_context: CallbackContext):
    """Callback triggered after each turn to save session facts, preferences, and user allergies to Memory Bank."""
    try:
        await callback_context.add_session_to_memory()
    except Exception:
        pass
    return None


def memory_bank_service_builder():
    """Builder for Vertex AI Memory Bank service when deployed or running with memory service."""
    return VertexAiMemoryBankService(
        project=PROJECT_ID,
        location="us-central1",
        agent_engine_id=MEMORY_BANK_ID,
    )


schema_manager = A2uiSchemaManager(
    version="0.8",
    catalogs=[BasicCatalog.get_config("0.8")],
)

a2ui_instruction = schema_manager.generate_system_prompt(
    role_description="You are Travel Concierge, an AI travel assistant.",
    workflow_description=(
        "You help users explore destinations, discover travel recommendations, search attractions by interest, geocode addresses, find nearby places/restaurants/attractions using Google Maps & Places, generate destination images and short destination videos using Gemini Omni model, check destination details, calculate itemized trip budgets, check live currency exchange rates, execute custom Python code/calculations in a secure sandbox, and manage saved travel spots in the Firestore database. Analyze the user request and return structured UI when appropriate."
    ),
    ui_description=(
        "MEMORY & ALLERGY SAFETY GUARDRAILS:\n"
        "- Explicitly remember and retain all user allergies (e.g., food allergies like peanuts, tree nuts, shellfish, gluten, dairy/lactose, or medical/environmental allergies) and dietary preferences mentioned during any conversation turn.\n"
        "- Ensure all stated allergies are sent to long-term memory so they persist across future sessions.\n"
        "- Whenever suggesting restaurants, local dining, or food tours, always check the user's remembered allergies and highlight safe options while cautioning against allergen risks.\n\n"
        "A2UI COMPONENT & DESIGN RULES:\n"
        "Keep every surface tiny and flat: ONE Card > ONE Column > a few Text rows. "
        "Never nest a Card inside a Card. "
        "Use ONLY these components: Card, Column, Row, Text, and Image. Do not use "
        "Table or Heading (unsupported), or Buttons, actions, or forms (they do "
        "nothing in adk web). "
        "You may include one Image component, but only when you have a public https "
        "URL for the image (for example the URL an image tool returns after uploading "
        "to a public bucket). Set the Image url to that exact https link, for example "
        '{"Image": {"url": {"literalString": "https://..."}}}. Never point an '
        "Image at a bare filename, an artifact name, or a non-http(s) path. If you do "
        "not have a public URL, add a short Text line noting the image instead. "
        "No markdown in text; use the usageHint property ('h1', 'h2', 'body') for "
        "headings and emphasis. "
        "Output ONLY the raw A2UI JSON array — no prose, and never wrap it in "
        "<a2a_datapart_json> tags or 'kind'/'data'/'metadata' objects."
    ),
    include_schema=True,
    include_examples=True,
)


root_agent = Agent(
    name="root_agent",
    model=Gemini(
        model="gemini-flash-latest",
        retry_options=types.HttpRetryOptions(attempts=3),
    ),
    instruction=a2ui_instruction,
    tools=[
        PreloadMemoryTool(),
        list_destinations,
        get_destination_details,
        add_destination,
        calculate_trip_budget,
        search_attractions_by_interest,
        get_currency_exchange_rate,
        geocode_address,
        find_nearby_places,
        generate_destination_image,
        generate_destination_video,
        get_weather,
        get_current_time,
    ],
    code_executor=code_executor,
    after_agent_callback=generate_memories_callback,
    after_model_callback=a2ui_callback,
)

app = App(
    root_agent=root_agent,
    name="app",
)
