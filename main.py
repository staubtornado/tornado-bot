from os import getenv, listdir, remove
from os.path import join
from sqlite3 import connect, Error, Connection
from time import time, localtime, strftime
from traceback import format_exc

from discord import Bot, ApplicationCommandInvokeError, ApplicationContext, CheckFailure, Interaction
from discord.ext.tasks import loop
from dotenv import load_dotenv
from tqdm import tqdm

from data.config.settings import SETTINGS
from data.db.memory import database
from lib.presence.presence import update_rich_presence
from lib.utils.utils import save_traceback

bot: Bot = Bot(owner_ids=SETTINGS["OwnerIDs"], description=SETTINGS["Description"], intents=SETTINGS["Intents"])

db_initialized: bool = False


@loop(seconds=SETTINGS["ServiceSyncInSeconds"])
async def sync_database():
    global db_initialized
    local_db: Connection = connect("./data/db/database.db", check_same_thread=False)

    print("[SYSTEM] Syncing database...")
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
        print(f"[FATAL ERROR] An error occurred while syncing database: {e}\n{format_exc()}")
    else:
        print("[SYSTEM] Synced database successfully.")
    local_db.close()


@bot.event
async def on_ready():
    bot.uptime = round(time())
    bot.latencies = []
    print(f"[SYSTEM] {bot.user} is online...")


@bot.event
async def on_interaction(interaction: Interaction):
    await bot.process_application_commands(interaction, auto_sync=None)

    if interaction.is_command():
        print(f"[DEFAULT] [{strftime('%d.%m.%y %H:%M', localtime())}] "
              f"{interaction.user} executed /{interaction.data['name']} in {interaction.guild}")


@bot.event
async def on_application_command_error(ctx: ApplicationContext, error):
    if not SETTINGS["Production"]:
        await ctx.respond(f"❌ An **error occurred**: `{error}`.")
        raise error
    save_traceback(error)
    print(f"[ERROR] [{strftime('%d.%m.%y %H:%M', localtime())}] {ctx.user} executed {ctx.command.name} in {ctx.guild}")

    if isinstance(error, CheckFailure):
        if ctx.command.name == "play":
            await ctx.respond("❌ This **command** is **restricted to beta** guilds.\n"
                              "👉 Use **/**`settings beta` to **enter the closed beta**.")
            return
        await ctx.respond("❌ This guild is **not permitted to use** that **command**.")
        return

    if isinstance(error, ApplicationCommandInvokeError):
        await ctx.respond(f"❌ An **error occurred**: `{error}`.")
        return
    raise error


def main():
    print(f"VERSION: {SETTINGS['Version']}\nCopyright (c) 2021 - present Staubtornado\n{'-' * 30}")
    load_dotenv("./data/config/.env")

    cache = "./data/cache"
    if len(listdir(cache)) > 0:
        for f in tqdm(listdir(cache), "[SYSTEM] Cleaning cache"):
            remove(join(cache, f))

    sync_database.start()
    update_rich_presence.start(bot)

    for filename in listdir('./cogs'):
        if filename.endswith('.py'):
            try:
                bot.load_extension(f'cogs.{filename[:-3]}')
            except Exception as e:
                print(f"[FATAL ERROR] Failed to load {filename}: {e} \n{format_exc()}")
    bot.run(getenv("DISCORD_BOT_TOKEN"))


if __name__ == "__main__":
    main()
