"""Compare current weather for a trip from ZIP code 75038 to 43035."""

import os

import requests
import truststore
from dotenv import load_dotenv
from strands import Agent, tool
from strands.models.openai import OpenAIModel

truststore.inject_into_ssl()


def fetch_current_weather(zip_code: str) -> dict:
    """Fetch live weather conditions for a US ZIP code."""
    location_response = requests.get(
        f"https://api.zippopotam.us/us/{zip_code}", timeout=10
    )
    location_response.raise_for_status()
    location = location_response.json()
    place = location["places"][0]

    weather_response = requests.get(
        "https://api.open-meteo.com/v1/forecast",
        params={
            "latitude": place["latitude"],
            "longitude": place["longitude"],
            "current": (
                "temperature_2m,apparent_temperature,relative_humidity_2m,"
                "precipitation,weather_code,wind_speed_10m"
            ),
            "temperature_unit": "fahrenheit",
            "wind_speed_unit": "mph",
            "timezone": "auto",
        },
        timeout=10,
    )
    weather_response.raise_for_status()

    return {
        "zip_code": zip_code,
        "location": f'{place["place name"]}, {place["state abbreviation"]}',
        "current_weather": weather_response.json()["current"],
    }


@tool
def compare_current_weather(origin_zip_code: str, destination_zip_code: str) -> dict:
    """Compare live weather between an origin and destination US ZIP code."""
    origin = fetch_current_weather(origin_zip_code)
    destination = fetch_current_weather(destination_zip_code)
    origin_weather = origin["current_weather"]
    destination_weather = destination["current_weather"]

    return {
        "origin": origin,
        "destination": destination,
        "destination_minus_origin": {
            "temperature_f": round(
                destination_weather["temperature_2m"] - origin_weather["temperature_2m"], 1
            ),
            "apparent_temperature_f": round(
                destination_weather["apparent_temperature"]
                - origin_weather["apparent_temperature"],
                1,
            ),
            "relative_humidity_percent": round(
                destination_weather["relative_humidity_2m"]
                - origin_weather["relative_humidity_2m"],
                1,
            ),
            "precipitation_in": round(
                destination_weather["precipitation"] - origin_weather["precipitation"], 2
            ),
            "wind_speed_mph": round(
                destination_weather["wind_speed_10m"] - origin_weather["wind_speed_10m"], 1
            ),
        },
    }


def main() -> None:
    load_dotenv()

    if not os.getenv("OPENAI_API_KEY"):
        raise RuntimeError("Set OPENAI_API_KEY before running this script.")

    model = OpenAIModel(
        client_args={"api_key": os.environ["OPENAI_API_KEY"]},
        model_id="gpt-4o-mini",
    )
    agent = Agent(model=model, tools=[compare_current_weather])
    agent(
        "I am traveling from ZIP code 75038 to ZIP code 43035. "
        "Compare the current weather at both locations, then recommend what to wear. "
        "Mention important temperature, precipitation, and wind differences."
    )


if __name__ == "__main__":
    main()