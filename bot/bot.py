"""
bot.py — BacktestingMax Discord Bot
MIT License — Copyright (c) 2026 Rishi Gopinath
Run: python bot.py
"""

import logging
import os
from datetime import datetime, timedelta, timezone

import discord
from discord import app_commands
from discord.ext import tasks
from dotenv import load_dotenv

from api_client import APIClient
from embeds import (
    challenge_embed, leaderboard_embed, lifetime_embed,
    stats_embed, winner_announcement_embed, error_embed
)

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("btmax.bot")

DISCORD_TOKEN           = os.getenv("DISCORD_TOKEN")
API_BASE_URL            = os.getenv("API_BASE_URL", "http://127.0.0.1:8000")
API_KEY                 = os.getenv("API_KEY", "mock-api-key-12345")
ANNOUNCEMENT_CHANNEL_ID = int(os.getenv("ANNOUNCEMENT_CHANNEL_ID", "0"))

if not DISCORD_TOKEN:
    raise ValueError("DISCORD_TOKEN not set in .env")


class BTMaxBot(discord.Client):
    def __init__(self):
        super().__init__(intents=discord.Intents.default())
        self.tree = app_commands.CommandTree(self)
        self.api  = APIClient(API_BASE_URL, API_KEY)

    async def setup_hook(self):
        await self.api.start()
        guild = discord.Object(id=1410323690826240132)
        self.tree.copy_global_to(guild=guild)
        await self.tree.sync(guild=guild)
        logger.info("Commands synced to guild.")
        daily_post.start()

    async def on_ready(self):
        logger.info("Online: %s (%s)", self.user, self.user.id)

    async def close(self):
        await self.api.close()
        await super().close()

bot = BTMaxBot()


# ── /challenge ─────────────────────────────────────────────────
@bot.tree.command(name="challenge", description="View today's Daily Backtest Challenge.")
async def cmd_challenge(interaction: discord.Interaction):
    await interaction.response.defer()
    try:
        data = await bot.api.get_daily_challenge()
        await interaction.followup.send(embed=challenge_embed(data))
    except Exception as e:
        logger.exception("challenge error:")
        await interaction.followup.send(embed=error_embed(str(e)))


# ── /leaderboard ───────────────────────────────────────────────
@bot.tree.command(name="leaderboard", description="Show top rankings for a given date.")
@app_commands.describe(date="Date in YYYY-MM-DD format (default: today)")
async def cmd_leaderboard(interaction: discord.Interaction, date: str = None):
    await interaction.response.defer()
    try:
        date = date or datetime.now(timezone.utc).strftime("%Y-%m-%d")
        data = await bot.api.get_leaderboard(date, limit=100)
        view = LeaderboardView(date, 0, data)
        await interaction.followup.send(embed=leaderboard_embed(data[:10], date, page=0), view=view)
    except Exception as e:
        logger.exception("leaderboard error:")
        await interaction.followup.send(embed=error_embed(str(e)))


# ── /lifetime ──────────────────────────────────────────────────
@bot.tree.command(name="lifetime", description="All-time participation leaderboard.")
async def cmd_lifetime(interaction: discord.Interaction):
    await interaction.response.defer(thinking=True)
    try:
        data = await bot.api.get_lifetime()
        view = LifetimeView(0, data)
        await interaction.followup.send(embed=lifetime_embed(data[:10], page=0), view=view)
    except Exception as e:
        logger.exception("lifetime error:")
        await interaction.followup.send(embed=error_embed(str(e)))


# ── /stats ─────────────────────────────────────────────────────
@bot.tree.command(name="stats", description="Look up a user's full profile and stats.")
@app_commands.describe(username="Username to look up")
async def cmd_stats(interaction: discord.Interaction, username: str):
    await interaction.response.defer(thinking=True)
    try:
        results = await bot.api.search_users(username)
        if not results:
            await interaction.followup.send(embed=error_embed(f"No user found: `{username}`"))
            return
        if len(results) == 1:
            stats = await bot.api.get_user_stats(results[0]["userId"])
            await interaction.followup.send(embed=stats_embed(stats))
        else:
            await interaction.followup.send(
                content="Multiple users found — select one:",
                view=UserSelectView(results[:25])
            )
    except Exception as e:
        logger.exception("stats error:")
        await interaction.followup.send(embed=error_embed(str(e)))


# ── Leaderboard pagination ─────────────────────────────────────
class LeaderboardView(discord.ui.View):
    def __init__(self, date, page, data):
        super().__init__(timeout=120)
        self.date = date
        self.page = page
        self.data = data
        self._rebuild()

    def _rebuild(self):
        self.clear_items()
        total_pages = max(1, (len(self.data) + 9) // 10)

        prev = discord.ui.Button(label="◀ Prev", style=discord.ButtonStyle.secondary,
                                  disabled=self.page == 0, row=0)
        prev.callback = self._prev
        self.add_item(prev)

        indicator = discord.ui.Button(
            label=f"Page {self.page + 1} / {total_pages}",
            style=discord.ButtonStyle.primary, disabled=True, row=0)
        self.add_item(indicator)

        nxt = discord.ui.Button(label="Next ▶", style=discord.ButtonStyle.secondary,
                                 disabled=(self.page + 1) * 10 >= len(self.data), row=0)
        nxt.callback = self._next
        self.add_item(nxt)

        if total_pages > 1:
            options = [
                discord.SelectOption(
                    label=f"Page {i+1}  (#{i*10+1}–#{min(i*10+10, len(self.data))})",
                    value=str(i), default=(i == self.page)
                )
                for i in range(min(total_pages, 25))
            ]
            select = discord.ui.Select(placeholder="Jump to page...", options=options, row=1)
            select.callback = self._jump
            self.add_item(select)

        from datetime import timedelta
        today = datetime.now(timezone.utc)
        date_options = []
        for i in range(14):
            d = today - timedelta(days=i)
            label = "Today" if i == 0 else ("Yesterday" if i == 1 else d.strftime("%b %d, %Y"))
            val = d.strftime("%Y-%m-%d")
            date_options.append(discord.SelectOption(
                label=label, value=val, default=(val == self.date)
            ))
        date_select = discord.ui.Select(placeholder="Pick a date...", options=date_options, row=2)
        date_select.callback = self._pick_date
        self.add_item(date_select)

    async def _prev(self, interaction):
        self.page -= 1
        await self._update(interaction)

    async def _next(self, interaction):
        self.page += 1
        await self._update(interaction)

    async def _jump(self, interaction):
        self.page = int(interaction.data["values"][0])
        await self._update(interaction)

    async def _pick_date(self, interaction):
        new_date = interaction.data["values"][0]
        await interaction.response.edit_message(content="Loading...", embed=None, view=None)
        try:
            data = await bot.api.get_leaderboard(new_date, limit=100)
            self.date = new_date
            self.page = 0
            self.data = data
            self._rebuild()
            await interaction.edit_original_response(
                content=None,
                embed=leaderboard_embed(data[:10], new_date, page=0),
                view=self
            )
        except Exception as e:
            await interaction.edit_original_response(content=None, embed=error_embed(str(e)), view=None)

    async def _update(self, interaction):
        start = self.page * 10
        page_data = self.data[start:start+10]
        self._rebuild()
        await interaction.response.edit_message(
            embed=leaderboard_embed(page_data, self.date, page=self.page), view=self)


# ── Lifetime pagination ────────────────────────────────────────
class LifetimeView(discord.ui.View):
    def __init__(self, page, data):
        super().__init__(timeout=120)
        self.page = page
        self.data = data
        self._rebuild()

    def _rebuild(self):
        self.clear_items()
        total_pages = max(1, (len(self.data) + 9) // 10)

        prev = discord.ui.Button(label="◀ Prev", style=discord.ButtonStyle.secondary,
                                  disabled=self.page == 0, row=0)
        prev.callback = self._prev
        self.add_item(prev)

        indicator = discord.ui.Button(
            label=f"Page {self.page + 1} / {total_pages}",
            style=discord.ButtonStyle.primary, disabled=True, row=0)
        self.add_item(indicator)

        nxt = discord.ui.Button(label="Next ▶", style=discord.ButtonStyle.secondary,
                                 disabled=(self.page + 1) * 10 >= len(self.data), row=0)
        nxt.callback = self._next
        self.add_item(nxt)

        if total_pages > 1:
            options = [
                discord.SelectOption(
                    label=f"Page {i+1}  (#{i*10+1}–#{min(i*10+10, len(self.data))})",
                    value=str(i), default=(i == self.page)
                )
                for i in range(min(total_pages, 25))
            ]
            select = discord.ui.Select(placeholder="Jump to page...", options=options, row=1)
            select.callback = self._jump
            self.add_item(select)

    async def _prev(self, interaction):
        self.page -= 1
        await self._update(interaction)

    async def _next(self, interaction):
        self.page += 1
        await self._update(interaction)

    async def _jump(self, interaction):
        self.page = int(interaction.data["values"][0])
        await self._update(interaction)

    async def _update(self, interaction):
        start = self.page * 10
        page_data = self.data[start:start+10]
        self._rebuild()
        await interaction.response.edit_message(
            embed=lifetime_embed(page_data, page=self.page), view=self)


# ── User select for /stats ─────────────────────────────────────
class UserSelectView(discord.ui.View):
    def __init__(self, users):
        super().__init__(timeout=60)
        options = [
            discord.SelectOption(label=u["username"][:100], value=u["userId"])
            for u in users
        ]
        select = discord.ui.Select(placeholder="Select a user...", options=options)
        select.callback = self._selected
        self.add_item(select)

    async def _selected(self, interaction):
        user_id = interaction.data["values"][0]
        await interaction.response.edit_message(content="Fetching stats...", view=None)
        try:
            stats = await bot.api.get_user_stats(user_id)
            await interaction.edit_original_response(
                content=None, embed=stats_embed(stats), view=None)
        except Exception as e:
            await interaction.edit_original_response(
                content=None, embed=error_embed(str(e)), view=None)


# ── Daily post ─────────────────────────────────────────────────
@tasks.loop(time=datetime.strptime("00:05", "%H:%M").time())
async def daily_post():
    if not ANNOUNCEMENT_CHANNEL_ID:
        return
    channel = bot.get_channel(ANNOUNCEMENT_CHANNEL_ID)
    if not channel:
        logger.error("Announcement channel %d not found", ANNOUNCEMENT_CHANNEL_ID)
        return
    yesterday = (datetime.now(timezone.utc) - timedelta(days=1)).strftime("%Y-%m-%d")
    try:
        data = await bot.api.get_leaderboard(yesterday, limit=10)
        await channel.send(embed=winner_announcement_embed(data, yesterday))
        logger.info("Posted daily winners for %s", yesterday)
    except Exception as e:
        logger.error("Daily post failed: %s", e)

@daily_post.before_loop
async def before_daily():
    await bot.wait_until_ready()


if __name__ == "__main__":
    bot.run(DISCORD_TOKEN, log_handler=None)