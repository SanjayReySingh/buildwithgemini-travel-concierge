import os
from google.cloud import firestore

# HARDCODED GCP Project ID (Do NOT use google.auth.default() or GOOGLE_CLOUD_PROJECT env var)
PROJECT_ID = "qwiklabs-gcp-03-4e2380eb54ba"

SEEDED_DESTINATIONS = [
    {
        "id": "tokyo",
        "name": "Tokyo",
        "country": "Japan",
        "category": "Culture & Food",
        "description": "A bustling metropolis blending ultra-modern skyscrapers with historic temples, renowned for world-class cuisine and vibrant technology.",
        "best_season": "Spring (Cherry Blossom) & Autumn",
        "avg_daily_cost": 220,
        "top_attractions": ["Shibuya Crossing", "Senso-ji Temple", "Tokyo Skytree", "Tsukiji Outer Market"],
    },
    {
        "id": "paris",
        "name": "Paris",
        "country": "France",
        "category": "Romance & Art",
        "description": "The City of Light, famous for iconic architecture, world-renowned museums, cafe culture, and exquisite gastronomy.",
        "best_season": "Spring & Autumn",
        "avg_daily_cost": 260,
        "top_attractions": ["Eiffel Tower", "Louvre Museum", "Notre-Dame Cathedral", "Montmartre"],
    },
    {
        "id": "kyoto",
        "name": "Kyoto",
        "country": "Japan",
        "category": "Culture & Nature",
        "description": "Japan's ancient capital, famous for classical Buddhist temples, gardens, imperial palaces, Shinto shrines, and traditional wooden houses.",
        "best_season": "Spring & Autumn",
        "avg_daily_cost": 180,
        "top_attractions": ["Fushimi Inari Taisha", "Kinkaku-ji (Golden Pavilion)", "Arashiyama Bamboo Grove"],
    },
    {
        "id": "rio",
        "name": "Rio de Janeiro",
        "country": "Brazil",
        "category": "Beach & Party",
        "description": "A vibrant coastal city famous for Copacabana and Ipanema beaches, Christ the Redeemer statue, Sugarloaf Mountain, and Carnival.",
        "best_season": "December to March",
        "avg_daily_cost": 150,
        "top_attractions": ["Christ the Redeemer", "Sugarloaf Mountain", "Copacabana Beach", "Selarón Steps"],
    },
    {
        "id": "reykjavik",
        "name": "Reykjavik",
        "country": "Iceland",
        "category": "Nature & Adventure",
        "description": "Gateway to Iceland's geothermal wonders, northern lights, dramatic glaciers, waterfalls, and volcanic landscapes.",
        "best_season": "Winter (Northern Lights) & Summer (Midnight Sun)",
        "avg_daily_cost": 300,
        "top_attractions": ["Blue Lagoon", "Golden Circle", "Hallgrímskirkja", "Harpa Concert Hall"],
    },
]

def seed_database():
    print(f"Connecting to Firestore with project ID: '{PROJECT_ID}'...")
    db = firestore.Client(project=PROJECT_ID)
    collection_ref = db.collection("destinations")

    print("Seeding destinations collection...")
    for item in SEEDED_DESTINATIONS:
        doc_id = item["id"]
        collection_ref.document(doc_id).set(item)
        print(f"  ✓ Added destination '{doc_id}' ({item['name']}, {item['country']})")

    print("\n✅ Firestore successfully seeded with travel destinations!")

if __name__ == "__main__":
    seed_database()
