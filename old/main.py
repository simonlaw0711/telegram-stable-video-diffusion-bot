import concurrent.futures
import uvicorn
from bot import start_bot  # Assuming your bot.py has a function to start the bot
import app  # Your FastAPI application

def start_telegram_bot():
    start_bot()  # Call the function that starts your Telegram bot

def start_fastapi_app():
    uvicorn.run(app.app, host="127.0.0.1", port=8000)

if __name__ == "__main__":
    # Using ThreadPoolExecutor to run both functions concurrently
    with concurrent.futures.ThreadPoolExecutor() as executor:
        executor.submit(start_telegram_bot)
        executor.submit(start_fastapi_app)
