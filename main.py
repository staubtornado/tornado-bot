from os import getenv, listdir, remove, mkdir
from os.path import join, exists
from traceback import format_exc

from discord import LoginFailure
from dotenv import load_dotenv
from tqdm import tqdm

from bot import CustomBot
from data.config.settings import SETTINGS
from lib.presence.presence import update_rich_presence


def main():
    bot: CustomBot = CustomBot(
        owner_ids=SETTINGS["OwnerIDs"],
        description=SETTINGS["Description"],
        intents=SETTINGS["Intents"],
    )

    print(f"VERSION: {SETTINGS['Version']}\nCopyright (c) 2021 - present Staubtornado\n{'-' * 30}")
    load_dotenv("./data/config/.env")

    cache: str = "./data/cache"
    if not exists(cache):
        mkdir(cache)
    if not exists("./data/tracebacks"):
        mkdir("./data/tracebacks")

    if len(listdir(cache)) > 0:
        for f in tqdm(listdir(cache), "[SYSTEM] Cleaning cache"):
            remove(join(cache, f))
    update_rich_presence.start(bot)

    for filename in listdir('./cogs'):
        if filename.endswith('.py'):
            try:
                bot.load_extension(f'cogs.{filename[:-3]}')
            except Exception as e:
                print(f"[FATAL ERROR] Failed to load {filename}: {e} \n{format_exc()}")

    try:
        bot.run(getenv("DISCORD_BOT_TOKEN"))
    except LoginFailure:
        print("[FATAL ERROR] Invalid token. Please check your .env file and visit "
              "https://discord.com/developers/applications to create a new token.")


if __name__ == "__main__":
    main()
