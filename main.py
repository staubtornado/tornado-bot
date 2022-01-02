from discord import Bot
from os import getenv
from dotenv import load_dotenv
from discord.ext import tasks
import logging

from lib.db import db

FMT = "[{levelname:^7}] {name}: {message}"

# FORMATS = {
#     logging.DEBUG: FMT,
#     logging.INFO: f"\33[36m{FMT}\33[0m",
#     logging.WARNING: f"\33[33m{FMT}\33[0m",
#     logging.ERROR: f"\33[31m{FMT}\33[0m",
#     logging.CRITICAL: f"\33[1m\33[31m{FMT}\33[0m"
# }
#
#
# class CustomFormatter(logging.Formatter):
#     def format(self, record):
#         log_fmt = FORMATS[record.levelno]
#         formatter = logging.Formatter(log_fmt, style="{")
#         return formatter.format(record)
#
#
# handler = logging.StreamHandler()
# handler.setFormatter(CustomFormatter())
# logging.basicConfig(
#     level=logging.DEBUG,
#     handlers=[handler],
# )
#
# log = logging.getLogger("coloured-logger")
#
# log.debug("This is a message")
# log.info("This is a message")
# log.warning("This is a message")


bot: Bot = Bot(description="A feature-rich bot based on Python 3.9 and Py-Cord.")

database: dict = {}
load_dotenv()


@tasks.loop(minutes=30)
async def update_db():
    print("Saving database...")
    try:
        db.commit()
    except Exception as e:
        print(f"Failed to save database: {e}")
    else:
        print("Saved database successfully...")

    print("Loading database...")

    # for db_name in db.execute("SELECT * FROM exp WHERE type = 'table'"):
    #     database[db_name] = None
    # print(database)

    # for x in database:
    #     db.execute('SELECT * FROM ' + x[0] + ' WHERE columnA" = "-"')
    #     stats = db.cur.fetchall()
    #     for stat in stats:
    #         print(stat, x)


update_db.start()


@bot.event
async def on_ready():
    print(f"{bot.user} is online...")


if __name__ == "__main__":
    print(
        f"VERSION: {None}\nCopyright (c) 2021 - present Staubtornado\n{'-' * 30}")  # TODO: ADD VERSION TO BOT START-UP MESSAGE
    bot.run(getenv("DISCORD_BOT_TOKEN"))
