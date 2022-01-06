from os import getenv, listdir
from sqlite3 import connect

from discord import Bot
from discord.ext import tasks
from dotenv import load_dotenv

from data.config.settings import SETTINGS
from lib.db import db

bot: Bot = Bot(owner_ids=SETTINGS["OwnerIDs"], description=SETTINGS["Description"], intents=SETTINGS["Intents"])

database: connect = connect(":memory:")
local_db: db.cxn = db.cxn

load_dotenv()


@tasks.loop(minutes=30)
async def sync_database():
    print("Syncing database...")

    try:
        database.backup(local_db)
        local_db.backup(database)
    except Exception as e:
        print(f"An error uncured while syncing database: {e}")
    else:
        print("Synced database successfully.")


@bot.event
async def on_ready():
    print(f"{bot.user} is online...")


def main():
    sync_database.start()

    for filename in listdir('./cogs'):
        if filename.endswith('.py'):
            bot.load_extension(f'cogs.{filename[:-3]}')

    print(
        f"VERSION: {None}\nCopyright (c) 2021 - present Staubtornado\n{'-' * 30}")  # TODO: ADD VERSION TO BOT START-UP MESSAGE
    bot.run(getenv("DISCORD_BOT_TOKEN"))


if __name__ == "__main__":
    main()
