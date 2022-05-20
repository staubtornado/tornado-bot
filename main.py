from asyncio import run
from os import getenv, listdir
from sqlite3 import connect, Error
from time import time
from traceback import format_exc

from discord import Bot, ApplicationCommandInvokeError, ApplicationContext
from discord.ext.tasks import loop
from dotenv import load_dotenv

from data.config.settings import SETTINGS
from data.db.memory import database
from lib.presence.presence import update_rich_presence

bot: Bot = Bot(owner_ids=SETTINGS["OwnerIDs"], description=SETTINGS["Description"], intents=SETTINGS["Intents"])

db_initialized: bool = False


@loop(seconds=SETTINGS["ServiceSyncInSeconds"])
async def sync_database():
    global db_initialized
    local_db: connect = connect("./data/db/database.db", check_same_thread=False)

    print("Syncing database...")
    try:
        if not db_initialized:
            with open("./data/db/build.sql", "r", encoding="utf-8") as script:
                local_db.cursor().executescript(script.read())
            local_db.commit()
            local_db.backup(database)
            db_initialized = True
        else:
            with database:
                database.commit()
                database.backup(local_db)
    except Error as e:
        print(f"An error occurred while syncing database: {e}\n{format_exc()}")
    else:
        print("Synced database successfully.")
    local_db.close()


@bot.event
async def on_ready():
    bot.uptime = round(time())
    print(f"{bot.user} is online...")


@bot.event
async def on_application_command_error(ctx: ApplicationContext, error):
    if not SETTINGS["Production"]:
        await ctx.respond(f"❌ An **error occurred**: `{error.original}`.")
        raise error

    if isinstance(error, ApplicationCommandInvokeError):
        await ctx.respond(f"❌ An **error occurred**: `{error.original}`.")
        return
    raise error


def main():
    print(f"VERSION: {SETTINGS['Version']}\nCopyright (c) 2021 - present Staubtornado\n{'-' * 30}")
    load_dotenv("./data/config/.env")

    sync_database.start()
    update_rich_presence.start(bot)

    for filename in listdir('./cogs'):
        if filename.endswith('.py'):
            try:
                bot.load_extension(f'cogs.{filename[:-3]}')
            except Exception as e:
                print(f"Failed to load {filename}: {e} \n{format_exc()}")
    bot.run(getenv("DISCORD_BOT_TOKEN"))  # TODO: FIX STRG + C NOT MAKING A SAVE BEFORE EXIT


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("Exiting script...")
        run(bot.close())
        run(sync_database())
