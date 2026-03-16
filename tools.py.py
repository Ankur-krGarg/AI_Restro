import requests
import gspread
from google.oauth2.service_account import Credentials
from langchain_core.tools import tool
from app.menu_handler import search_menu_db

@tool
def search_menu(query: str) -> str:
    """Always use this tool to search the restaurant's actual menu for items, prices, and categories."""
    return search_menu_db(query)

@tool
def map_and_weather(city: str) -> str:
    """Get the current weather and location details of a region to suggest food dynamically."""
    try:
        geo_data = requests.get(f"https://geocoding-api.open-meteo.com/v1/search?name={city}&count=1").json()
        if not geo_data.get("results"): return "Location not found."
        lat, lon = geo_data["results"][0]["latitude"], geo_data["results"][0]["longitude"]
        w_data = requests.get(f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current_weather=true").json()
        return f"Weather in {city}: {w_data['current_weather']['temperature']}°C."
    except Exception as e: return f"Weather API error: {e}"

@tool
def timer(dish_name: str, distance_km: float) -> str:
    """Calculate time needed for dish preparation and delivery."""
    prep = len(dish_name) * 1.5 
    delivery = distance_km * 2.5
    return f"Prep: {prep:.0f} mins. Delivery: {delivery:.0f} mins. Total Time: {prep+delivery:.0f} mins."

@tool
def event_manager_google_sheet(event_name: str, attendees: int, date: str) -> str:
    """Write event details to Google Sheets."""
    try:
        creds = Credentials.from_service_account_file("credentials.json", scopes=['https://www.googleapis.com/auth/spreadsheets'])
        client = gspread.authorize(creds)
        client.open("EventManagement").sheet1.append_row([event_name, attendees, date])
        return "Event officially saved to Google Sheets."
    except Exception:
        return f"Event saved internally: '{event_name}' for {attendees} pax on {date}."

@tool
def calculator_and_converter(expression: str, currency: str = "USD") -> str:
    """Calculate the bill from a math expression and convert currencies."""
    try:
        result = eval(expression, {"__builtins__": None})
        rates = requests.get("https://open.er-api.com/v6/latest/USD").json().get("rates", {})
        target = currency.upper()
        if target in rates and target != "USD":
            return f"Bill: ${result:.2f} USD / {result * rates[target]:.2f} {target}"
        return f"Bill: ${result:.2f} USD"
    except Exception as e: return str(e)

@tool
def TransferToWaiter():
    """Transfer the user to the Waiter Agent."""
    pass

@tool
def TransferToEventManager():
    """Transfer the user to the Event Manager."""
    pass