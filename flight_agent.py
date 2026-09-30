"""Coordinate weather, flight, and recommendation agents for a seven-day trip plan."""

import json
import os

import requests
import truststore
from dotenv import load_dotenv
from strands import Agent, tool
from strands.models.openai import OpenAIModel

SERPAPI_URL = "https://serpapi.com/search.json"
ORIGIN_AIRPORT = "DFW"
DESTINATION_AIRPORT = "CMH"
ORIGIN_ZIP_CODE = "75038"
DESTINATION_ZIP_CODE = "43035"
MINIMUM_DESTINATION_TEMPERATURE_F = 60

truststore.inject_into_ssl()


def find_cheapest_flight(departure_date: str) -> dict:
    """Find the cheapest available one-way DFW-to-CMH flight for a YYYY-MM-DD date."""
    response = requests.get(
        SERPAPI_URL,
        params={
            "engine": "google_flights",
            "departure_id": ORIGIN_AIRPORT,
            "arrival_id": DESTINATION_AIRPORT,
            "outbound_date": departure_date,
            "type": 2,
            "currency": "USD",
            "api_key": os.environ["SERPAPI_API_KEY"],
        },
        timeout=20,
    )
    response.raise_for_status()
    flight_data = response.json()
    if "error" in flight_data:
        raise RuntimeError(f'SerpApi error: {flight_data["error"]}')

    offers = flight_data.get("best_flights", []) + flight_data.get("other_flights", [])
    if not offers:
        return {"message": "No available flights were found for that date."}

    cheapest_offer = min(offers, key=lambda offer: offer["price"])
    segments = cheapest_offer["flights"]

    return {
        "route": "Irving, TX (DFW) to Lewis Center, OH (CMH)",
        "departure_date": departure_date,
        "total_price": cheapest_offer["price"],
        "currency": "USD",
        "number_of_stops": len(segments) - 1,
        "duration": cheapest_offer.get("total_duration"),
        "airlines": sorted({segment["airline"] for segment in segments}),
        "segments": [
            {
                "flight": segment["flight_number"],
                "airline": segment["airline"],
                "departure_airport": segment["departure_airport"],
                "arrival_airport": segment["arrival_airport"],
            }
            for segment in segments
        ],
    }


def get_destination_forecast() -> list[dict]:
    """Return the next seven daily high-temperature forecasts for the destination ZIP."""
    location_response = requests.get(
        f"https://api.zippopotam.us/us/{DESTINATION_ZIP_CODE}", timeout=15
    )
    location_response.raise_for_status()
    place = location_response.json()["places"][0]

    forecast_response = requests.get(
        "https://api.open-meteo.com/v1/forecast",
        params={
            "latitude": place["latitude"],
            "longitude": place["longitude"],
            "daily": "temperature_2m_max",
            "temperature_unit": "fahrenheit",
            "forecast_days": 7,
            "timezone": "auto",
        },
        timeout=15,
    )
    forecast_response.raise_for_status()
    daily_forecast = forecast_response.json()["daily"]

    return [
        {"date": forecast_date, "high_temperature_f": high_temperature}
        for forecast_date, high_temperature in zip(
            daily_forecast["time"], daily_forecast["temperature_2m_max"], strict=True
        )
    ]


@tool
def get_warm_travel_dates() -> dict:
    """Find next-seven-day destination dates with a forecast high above 60 F."""
    forecast = get_destination_forecast()
    eligible_dates = [
        daily_weather
        for daily_weather in forecast
        if daily_weather["high_temperature_f"] > MINIMUM_DESTINATION_TEMPERATURE_F
    ]
    if not eligible_dates:
        return {
            "message": (
                f"No dates in the next seven days have a forecast high above "
                f"{MINIMUM_DESTINATION_TEMPERATURE_F} F at the destination."
            ),
            "destination_forecast": forecast,
        }

    return {
        "origin_zip_code": ORIGIN_ZIP_CODE,
        "destination_zip_code": DESTINATION_ZIP_CODE,
        "weather_rule": (
            f"Destination forecast high must be above "
            f"{MINIMUM_DESTINATION_TEMPERATURE_F} F."
        ),
        "eligible_dates": eligible_dates,
    }


@tool
def find_cheapest_flight_for_dates(departure_dates: list[str]) -> dict:
    """Find the cheapest available one-way DFW-to-CMH flight across specified dates."""
    flight_options = []
    for departure_date in departure_dates:
        flight_offer = find_cheapest_flight(departure_date)
        if "total_price" in flight_offer:
            flight_options.append(flight_offer)

    if not flight_options:
        return {"message": "No available flights were found on the eligible dates."}

    return {
        "searched_dates": departure_dates,
        "cheapest_flight": min(flight_options, key=lambda offer: offer["total_price"]),
    }


class TravelOrchestrator:
    """Coordinate specialist agents to create a weather-aware flight recommendation."""

    def __init__(self, model: OpenAIModel) -> None:
        self.weather_agent = Agent(
            model=model,
            name="weather_specialist",
            system_prompt=(
                "You are a weather specialist. Explain the destination forecast and which "
                "dates satisfy the requested temperature rule."
            ),
        )
        self.flight_agent = Agent(
            model=model,
            name="flight_specialist",
            system_prompt=(
                "You are a flight specialist. Use your tool to find the lowest available "
                "fare among the provided dates. Report price, airline, stops, and timing."
            ),
            tools=[find_cheapest_flight_for_dates],
        )
        self.advisor_agent = Agent(
            model=model,
            name="travel_advisor",
            system_prompt=(
                "You are a travel advisor. Combine the weather and flight specialist "
                "results into one concise recommendation. Do not invent unavailable details."
            ),
        )

    def plan_trip(self) -> None:
        weather_data = get_warm_travel_dates()
        weather_result = self.weather_agent(
            "Summarize this destination weather assessment: "
            f"{json.dumps(weather_data)}"
        )

        eligible_dates = [item["date"] for item in weather_data["eligible_dates"]]
        if not eligible_dates:
            print("No travel dates meet the destination weather requirement.")
            return

        flight_result = self.flight_agent(
            "Find the cheapest flight for these eligible departure dates: "
            f"{json.dumps(eligible_dates)}"
        )
        self.advisor_agent(
            "Weather specialist result: "
            f"{json.dumps(weather_result.to_dict()['message'])}\n\n"
            "Flight specialist result: "
            f"{json.dumps(flight_result.to_dict()['message'])}"
        )


def main() -> None:
    load_dotenv()
    required_variables = ("OPENAI_API_KEY", "SERPAPI_API_KEY")
    missing_variables = [name for name in required_variables if not os.getenv(name)]
    if missing_variables:
        raise RuntimeError(f"Set {', '.join(missing_variables)} in .env before running.")

    model = OpenAIModel(
        client_args={"api_key": os.environ["OPENAI_API_KEY"]},
        model_id="gpt-4o-mini",
    )
    TravelOrchestrator(model).plan_trip()


if __name__ == "__main__":
    main()