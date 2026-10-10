"""Fallback data for when APIs fail or LLM is unavailable."""

from typing import List, Dict, Any
from ..schemas import Place


# Curated fallback places for Kozhikode matching frontend data
FALLBACK_PLACES = [
    Place(
        id="mananchira",
        name="Mananchira Square",
        lat=11.2588,
        lng=75.7804,
        categories=["nature", "culture"],
        tags={
            "leisure": "park",
            "name": "Mananchira Square",
            "description": "Public park with tank in city center"
        },
        opening_status="open",
        facts=[
            "Description: Public park with tank in city center",
            "Popular gathering spot for locals"
        ]
    ),
    Place(
        id="smstreet", 
        name="SM Street (Mittai Theruvu)",
        lat=11.2575,
        lng=75.781,
        categories=["food"],
        tags={
            "highway": "pedestrian",
            "name": "SM Street",
            "alt_name": "Mittai Theruvu",
            "description": "Famous sweet street in Kozhikode"
        },
        opening_status="open",
        facts=[
            "Description: Famous sweet street in Kozhikode",
            "Known for traditional halwa and sweets"
        ]
    ),
    Place(
        id="beach",
        name="Kozhikode Beach", 
        lat=11.2623,
        lng=75.767,
        categories=["nature"],
        tags={
            "natural": "beach",
            "name": "Kozhikode Beach",
            "description": "Main public beach facing Arabian Sea"
        },
        opening_status="open",
        facts=[
            "Description: Main public beach facing Arabian Sea",
            "Popular evening destination with old pier remains"
        ]
    )
]


# Template mission data for fallback mode
FALLBACK_MISSION_TEMPLATES = {
    "mananchira": {
        "title": "The Quiet Centre",
        "intro": "The case begins where the city goes still.",
        "riddle": "A park wraps around still water in the middle of a busy city. Locals gather on its lawns, and the square is named for the water itself, not for any person. Where do you stand?",
        "hints": [
            "Think of a public square with a large tank (pond) at its heart.",
            "The name starts with 'Mana' and ends in 'chira'."
        ],
        "answers": [
            "mananchira",
            "mananchira square", 
            "mananchira maidan",
            "mananchira veedan maidan"
        ],
        "story": "Mananchira Square is a public park built around a large tank in the heart of Kozhikode. It is a favourite spot for walks and gatherings.",
        "activity": "Walk once around the tank and note what people are doing on the lawns."
    },
    "smstreet": {
        "title": "The Sweet Trail",
        "intro": "The next lead is something you can smell before you see it.",
        "riddle": "A crowded lane takes its popular name from sugar. Shops here are known for a sticky, ghee-rich sweet sold by weight. Name the street.",
        "hints": [
            "Its nickname in Malayalam means 'sweet street'.",
            "SM stands for 'Sweetmeat'."
        ],
        "answers": [
            "sm street",
            "s m street",
            "mittai theruvu",
            "mithai theruvu", 
            "sweet meat street",
            "sweetmeat street",
            "mittayi theruvu"
        ],
        "story": "SM Street, officially Sweet Meat Street and widely called Mittai Theruvu, is a busy shopping lane in central Kozhikode known for its sweets, especially halwa.",
        "activity": "Buy a small portion of halwa to share. Prices vary by shop, so ask before buying."
    },
    "beach": {
        "title": "Where the City Meets the Sea",
        "intro": "Final chapter. Follow the sound of the waves.",
        "riddle": "The Arabian Sea ends this case. Old piers once reached out from this shore, and people come here as the sun drops. Where does the trail end?",
        "hints": [
            "Look west. The city's main public shoreline.",
            "Remains of old piers stand in its waters."
        ],
        "answers": [
            "kozhikode beach",
            "calicut beach", 
            "beach",
            "kozhikode beach front",
            "calicut beach front"
        ],
        "story": "Kozhikode Beach is the city's main public shoreline on the Arabian Sea, popular in the evenings. Remains of old piers stand offshore.",
        "activity": "Watch the water from the shore. Stay on the open sand, away from the waterline when it is rough."
    }
}


def get_fallback_places() -> List[Place]:
    """Get fallback places when API fails."""
    return FALLBACK_PLACES.copy()


def get_fallback_mission_data(place_id: str) -> Dict[str, Any]:
    """Get template mission data for a place ID."""
    return FALLBACK_MISSION_TEMPLATES.get(place_id, {
        "title": "Mystery Location",
        "intro": "A new location to explore.",
        "riddle": f"Find this interesting place and discover what makes it special.",
        "hints": [
            "Look for local landmarks and signs.",
            "Ask locals for directions if needed."
        ],
        "answers": [place_id.lower()],
        "story": "This location has its own unique character and history.",
        "activity": "Take a moment to observe and appreciate the surroundings."
    })