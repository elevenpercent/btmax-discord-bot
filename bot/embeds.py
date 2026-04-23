"""
embeds.py — Pure functions mapping API JSON → discord.Embed objects.
Also builds quickchart.io URLs for placement histograms.
"""

import random
import urllib.parse
import json
import discord
from datetime import datetime

# ── Brand colors ───────────────────────────────────────────────
ORANGE = 0xFF6600
GOLD   = 0xFFAA00
RED    = 0xFF3333
GREEN  = 0x00FF88

# ── Flavor text (subtle, not "loading") ───────────────────────
CHALLENGE_SUBTITLES = [
    "Your next edge awaits.",
    "Time to prove your strategy.",
    "Can you beat the market today?",
    "One symbol. One chance. Let's go.",
    "Study the chart. Trust the process.",
]

LB_SUBTITLES = [
    "Ranked by profit percentage.",
    "The market doesn't lie.",
    "Who's on top today?",
    "Separating signal from noise.",
]

WINNER_SUBTITLES = [
    "The market has spoken.",
    "Another day, another edge.",
    "Consistency wins. Here's proof.",
]

# ── Helpers ────────────────────────────────────────────────────
def rank_emoji(rank: int) -> str:
    return {1: "🥇", 2: "🥈", 3: "🥉"}.get(rank, f"**#{rank}**")

def pro_badge(status: str) -> str:
    return "  `💎 PRO`" if status == "pro" else ""

def format_countdown(seconds: int) -> str:
    h, rem = divmod(seconds, 3600)
    m, s   = divmod(rem, 60)
    return f"{h}h {m}m {s}s"

def placement_chart_url(placements: dict) -> str:
    """Build a quickchart.io bar chart URL for placement distribution."""
    labels = ["1st", "2nd", "3rd", "Top 10"]
    values = [
        placements.get("1", 0),
        placements.get("2", 0),
        placements.get("3", 0),
        placements.get("top10", 0),
    ]
    chart = {
        "type": "bar",
        "data": {
            "labels": labels,
            "datasets": [{
                "label": "Placements",
                "data": values,
                "backgroundColor": ["#FF6600", "#FFAA00", "#FF8800", "#FF4400"],
                "borderRadius": 4,
            }]
        },
        "options": {
            "plugins": {
                "legend": {"display": False},
                "title": {
                    "display": True,
                    "text": "Placement History",
                    "color": "#FFFFFF",
                    "font": {"size": 16}
                }
            },
            "scales": {
                "x": {"ticks": {"color": "#CCCCCC"}, "grid": {"color": "#333333"}},
                "y": {"ticks": {"color": "#CCCCCC"}, "grid": {"color": "#333333"}, "beginAtZero": True}
            },
            "backgroundColor": "#1A1A1A"
        }
    }
    encoded = urllib.parse.quote(json.dumps(chart))
    return f"https://quickchart.io/chart?c={encoded}&backgroundColor=%231A1A1A&width=400&height=200"


# ── Embeds ─────────────────────────────────────────────────────

def challenge_embed(data: dict) -> discord.Embed:
    embed = discord.Embed(
        title="🎯  Daily Backtest Challenge",
        description=f"*{random.choice(CHALLENGE_SUBTITLES)}*",
        color=ORANGE
    )
    embed.add_field(name="📅  Date",      value=f"```{data['date']}```",                              inline=True)
    embed.add_field(name="📊  Symbol",    value=f"```{data['symbol'].upper()}```",                    inline=True)
    embed.add_field(name="⏳  Resets In", value=f"```{format_countdown(data['seconds_until_reset'])}```", inline=True)
    embed.add_field(
        name="\u200b",
        value="> Backtest this symbol and submit your results to compete on the leaderboard.",
        inline=False
    )
    embed.set_footer(text="BacktestingMax  •  Daily Challenge")
    return embed


def leaderboard_embed(data: list, date: str) -> discord.Embed:
    today = datetime.utcnow().strftime("%Y-%m-%d")
    label = "Today" if date == today else date
    embed = discord.Embed(
        title=f"🏆  Leaderboard  —  {label}",
        description=f"*{random.choice(LB_SUBTITLES)}*",
        color=GOLD
    )
    if not data:
        embed.description = "*No entries yet for this date.*"
        return embed
    lines = []
    for e in data[:10]:
        arrow = "▲" if e["profitPercent"] >= 0 else "▼"
        name  = e["username"] + pro_badge(e.get("subscriptionStatus", ""))
        lines.append(
            f"{rank_emoji(e['rank'])}  {name}\n"
            f"　`{arrow} {e['profitPercent']:+.2f}%`  ·  Win Rate `{e['winRate']:.1f}%`"
        )
    embed.description = (f"*{random.choice(LB_SUBTITLES)}*\n\n" + "\n\n".join(lines))
    embed.set_footer(text=f"BacktestingMax  •  Rankings for {label}")
    return embed


def lifetime_embed(data: list) -> discord.Embed:
    embed = discord.Embed(
        title="🌟  All-Time Participation Leaders",
        description="*The most dedicated traders on BacktestingMax.*",
        color=ORANGE
    )
    lines = []
    for e in data[:10]:
        name = e["username"] + pro_badge(e.get("subscriptionStatus", ""))
        lines.append(
            f"{rank_emoji(e['rank'])}  {name}\n"
            f"　`{e['totalDailyChallenges']} challenges`  ·  Avg `{e['avgProfitPercent']:+.1f}%`"
        )
    embed.description = "*The most dedicated traders on BacktestingMax.*\n\n" + "\n\n".join(lines)
    embed.set_footer(text="BacktestingMax  •  Lifetime Stats")
    return embed


def stats_embed(data: dict) -> discord.Embed:
    name  = data["username"]
    p     = data.get("placements", {})
    streak = data.get("currentStreak", 0)

    badges = []
    if data["completedChallenges"] >= 100:      badges.append("`💯 Century Club`")
    if p.get("1", 0) >= 5:                       badges.append("`👑 5x Champion`")
    if data["winRate"] >= 70:                    badges.append("`🎯 Sharp Shooter`")
    if streak >= 10:                              badges.append(f"`🔥 {streak}-Day Streak`")
    elif streak >= 5:                             badges.append(f"`⚡ {streak}-Day Streak`")
    if data.get("subscriptionStatus") == "pro":  badges.append("`💎 Pro Member`")

    embed = discord.Embed(
        title=f"📊  {name}",
        color=ORANGE
    )
    embed.add_field(name="Challenges",   value=f"```{data['completedChallenges']}```",      inline=True)
    embed.add_field(name="Win Rate",     value=f"```{data['winRate']:.1f}%```",             inline=True)
    embed.add_field(name="Avg Profit",   value=f"```{data['avgProfitPercent']:+.2f}%```",   inline=True)
    embed.add_field(name="Best Profit",  value=f"```{data['bestProfitPercent']:+.2f}%```",  inline=True)
    embed.add_field(name="🥇 1st Place", value=f"```{p.get('1', 0)}x```",                   inline=True)
    embed.add_field(name="Top 10",       value=f"```{p.get('top10', 0)}x```",               inline=True)

    if streak > 0:
        embed.add_field(name="🔥 Current Streak", value=f"```{streak} days```", inline=False)

    if badges:
        embed.add_field(name="🏅  Achievements", value="  ".join(badges), inline=False)

    # Placement histogram via quickchart.io
    chart_url = placement_chart_url(p)
    embed.set_image(url=chart_url)
    embed.set_footer(text="BacktestingMax  •  Player Profile")
    return embed


def winner_announcement_embed(data: list, date: str) -> discord.Embed:
    embed = discord.Embed(
        title=f"🏆  Daily Winners  —  {date}",
        description=f"*{random.choice(WINNER_SUBTITLES)}*",
        color=GOLD
    )
    for e in data[:3]:
        arrow = "▲" if e["profitPercent"] >= 0 else "▼"
        name  = e["username"] + pro_badge(e.get("subscriptionStatus", ""))
        embed.add_field(
            name=f"{rank_emoji(e['rank'])}  {name}",
            value=f"`{arrow} {e['profitPercent']:+.2f}%` profit  ·  `{e.get('winRate', 0):.1f}%` win rate",
            inline=False
        )
    embed.set_footer(text="BacktestingMax  •  Daily Challenge Results")
    return embed


def error_embed(message: str) -> discord.Embed:
    return discord.Embed(
        title="⚠️  Something went wrong",
        description=f"```{message}```",
        color=RED
    ).set_footer(text="BacktestingMax  •  Error")
