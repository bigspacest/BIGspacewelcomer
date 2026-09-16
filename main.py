import os
import threading
from flask import Flask
from dotenv import load_dotenv
import discord
from discord.ext import commands

load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")
if not TOKEN:
    raise ValueError("DISCORD_TOKEN environment variable is required")

# Intents necesarios
intents = discord.Intents.default()
intents.members = True          # obligatorio para on_member_join
intents.message_content = True  # solo si lo necesitas en otras partes

bot = commands.Bot(command_prefix="!", intents=intents)

# ---------- Flask keep-alive (UptimeRobot) ----------
app = Flask(__name__)

@app.route("/")
@app.route("/ping")
def ping():
    return "Bot is online", 200

def run_flask():
    # 0.0.0.0 para que UptimeRobot pueda alcanzarlo
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 8080)), debug=False)

# ---------- Bot events ----------
@bot.event
async def on_ready():
    print(f"Logged in as {bot.user} (ID: {bot.user.id})")
    try:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} slash command(s)")
    except Exception as e:
        print(f"Failed to sync commands: {e}")

async def load_extensions():
    await bot.load_extension("welcomer")

async def main():
    async with bot:
        await load_extensions()
        await bot.start(TOKEN)

if __name__ == "__main__":
    # Arrancar Flask en un hilo daemon
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()

    # Arrancar el bot
    import asyncio
    asyncio.run(main())
