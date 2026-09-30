# Strands Travel Agent Demo

A Python demo that uses the Strands SDK and OpenAI to provide live weather guidance and plan a weather-aware flight search.

## Features

- Compares current weather between ZIP codes `75038` (Irving, TX) and `43035` (Lewis Center, OH), then recommends what to wear.
- Uses three specialist agents coordinated by an orchestrator to plan a trip from `75038` to `43035`.
- Filters the next seven days to destination dates forecast above `60 F`.
- Finds the lowest available one-way fare from Dallas/Fort Worth (`DFW`) to Columbus (`CMH`) for the eligible dates.
- Uses OpenAI to turn the weather and flight data into a concise recommendation.

## Requirements

- Python 3.10 or newer
- An OpenAI API key
- A SerpApi key with Google Flights search access

## Setup

Install dependencies:

```powershell
python -m pip install -r requirements.txt
```

Create a local `.env` file based on `.env.example`:

```env
OPENAI_API_KEY=your_openai_api_key
SERPAPI_API_KEY=your_serpapi_api_key
```

Do not commit or upload `.env`. It contains API secrets and is excluded by `.gitignore`.

## Run The Weather Agent

```powershell
python weather_agent.py
```

The agent retrieves live weather for both ZIP codes, compares temperature, feels-like temperature, humidity, precipitation, and wind, then offers clothing advice.

## Run The Travel Planner

```powershell
python flight_agent.py
```

The `TravelOrchestrator` coordinates three Strands agents:

1. `weather_specialist` summarizes the seven-day forecast and identifies dates above `60 F`.
2. `flight_specialist` calls SerpApi Google Flights to search eligible dates and selects the lowest fare.
3. `travel_advisor` combines those results into the final travel recommendation.

## APIs Used

- [OpenAI](https://platform.openai.com/): language model used by the Strands agents.
- [Open-Meteo](https://open-meteo.com/): daily and current weather data.
- [Zippopotam](https://www.zippopotam.us/): ZIP code location lookup.
- [SerpApi Google Flights](https://serpapi.com/google-flights-api): live flight search results.

## Notes

- Flight prices and availability change frequently; results are informational and are not bookings.
- The flight search uses a one-way `DFW` to `CMH` itinerary for one adult.
- `truststore` enables HTTPS requests to use the Windows certificate store in this environment.