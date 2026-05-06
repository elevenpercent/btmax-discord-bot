import random
import urllib.parse
import json
import discord
from datetime import datetime, timezone

ORANGE = 0xFF6600
RED    = 0xFF3333

LOGO = "https://backtestingmax.com/favicon.ico"

def rank_emoji(rank):
    return {1: "🥇", 2: "🥈", 3: "🥉"}.get(rank, f"**#{rank}**")

def pro_badge(status):
    s = str(status).lower()
    return "  `💎 PRO`" if s == "pro" else ""

def format_countdown(seconds):
    h, rem = divmod(int(seconds), 3600)
    m, s = divmod(rem, 60)
    return f"{h}h {m}m {s}s"

def placement_chart_url(placements):
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
                "backgroundColor": ["#FF6600", "#FF8800", "#FF4400", "#FF5500"],
                "borderRadius": 4,
            }]
        },
        "options": {
            "plugins": {
                "legend": {"display": False},
                "title": {"display": True, "text": "Placement History", "color": "#FFFFFF", "font": {"size": 16}}
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


def challenge_embed(data):
    embed = discord.Embed(title="🎯  Daily Backtest Challenge", color=ORANGE)
    embed.add_field(name="📅  Date",      value=f"```{data.get('date', 'N/A')}```", inline=True)
    embed.add_field(name="📊  Symbol",    value=f"```{data.get('symbol', 'N/A').upper()}```", inline=True)
    embed.add_field(name="⏳  Resets In", value=f"```{format_countdown(data.get('seconds_until_reset', 0))}```", inline=True)
    embed.set_footer(text="BacktestingMax  •  Daily Challenge")
    return embed


def leaderboard_embed(data, date, page=0):
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    label = "Today" if date == today else date
    embed = discord.Embed(title=f"🏆  Leaderboard  —  {label}", color=ORANGE)
    if not data:
        embed.description = "*No entries yet for this date.*"
        return embed
    lines = []
    start = page * 10
    for i, e in enumerate(data[:10]):
        profit   = e.get("profitPercent", e.get("profit", 0))
        win_rate = e.get("winRate", 0)
        username = e.get("username", "Unknown")
        status   = e.get("subscription", "")
        symbol   = e.get("symbol", "")
        arrow    = "▲" if profit >= 0 else "▼"
        name     = str(username) + pro_badge(status)
        sym_tag  = f"  `{symbol}`" if symbol else ""
        lines.append(f"{rank_emoji(start + i + 1)}  {name}{sym_tag}\n　`{arrow} {profit:+.2f}%`  ·  Win Rate `{win_rate:.1f}%`")
    embed.description = "\n\n".join(lines)
    embed.set_footer(text=f"BacktestingMax  •  Page {page+1}  (#{start+1}–#{start+len(data[:10])})  •  For older dates: /leaderboard [date]")
    return embed


def lifetime_embed(data, page=0):
    embed = discord.Embed(title="🌟  All-Time Participation Leaders", color=ORANGE)
    if not data:
        embed.description = "*No data available.*"
        return embed
    lines = []
    start = page * 10
    for i, e in enumerate(data[:10]):
        username = e.get("username", "Unknown")
        total    = e.get("totalDailyChallenges", 0)
        status   = e.get("subscription", "")
        name     = str(username) + pro_badge(status)
        lines.append(f"{rank_emoji(start + i + 1)}  {name}\n　`{total} challenges`")
    embed.description = "\n\n".join(lines)
    embed.set_footer(text=f"BacktestingMax  •  Page {page+1}  (#{start+1}–#{start+len(data[:10])})  •  For older dates: /leaderboard [date]")
    return embed


def stats_embed(data):
    name      = data.get("username", "Unknown")
    p         = data.get("placements", {})
    streak    = data.get("currentStreak", data.get("streak", 0))
    completed = data.get("completedChallenges", data.get("completed", 0))
    avg       = data.get("avgProfitPercent", data.get("avg_profit", 0))
    best      = data.get("bestProfitPercent", data.get("best_profit", 0))
    wr        = data.get("winRate", data.get("win_rate", 0))
    status    = data.get("subscriptionStatus", data.get("subscription", ""))

    badges = []
    if completed >= 100:             badges.append("`💯 Century Club`")
    if p.get("1", 0) >= 5:           badges.append("`👑 5x Champion`")
    if wr >= 70:                     badges.append("`🎯 Sharp Shooter`")
    if streak >= 10:                 badges.append(f"`🔥 {streak}-Day Streak`")
    elif streak >= 5:                badges.append(f"`⚡ {streak}-Day Streak`")
    if str(status).lower() == "pro": badges.append("`💎 Pro Member`")

    embed = discord.Embed(title=f"📊  {name}", color=ORANGE)
    embed.add_field(name="Challenges",   value=f"```{completed}```",          inline=True)
    embed.add_field(name="Win Rate",     value=f"```{wr:.1f}%```",            inline=True)
    embed.add_field(name="Avg Profit",   value=f"```{avg:+.2f}%```",          inline=True)
    embed.add_field(name="Best Profit",  value=f"```{best:+.2f}%```",         inline=True)
    embed.add_field(name="🥇 1st Place", value=f"```{p.get('1', 0)}x```",     inline=True)
    embed.add_field(name="Top 10",       value=f"```{p.get('top10', 0)}x```", inline=True)
    if streak > 0:
        embed.add_field(name="🔥 Current Streak", value=f"```{streak} days```", inline=False)
    if badges:
        embed.add_field(name="🏅  Achievements", value="  ".join(badges), inline=False)
    embed.set_image(url=placement_chart_url(p))
    embed.set_footer(text="BacktestingMax  •  Player Profile")
    return embed


def winner_announcement_embed(data, date):
    embed = discord.Embed(title=f"🏆  Daily Winners  —  {date}", color=ORANGE)
    for i, e in enumerate(data[:3]):
        profit   = e.get("profitPercent", e.get("profit", 0))
        win_rate = e.get("winRate", 0)
        username = e.get("username", "Unknown")
        status   = e.get("subscription", "")
        arrow    = "▲" if profit >= 0 else "▼"
        name     = str(username) + pro_badge(status)
        embed.add_field(
            name=f"{rank_emoji(i+1)}  {name}",
            value=f"`{arrow} {profit:+.2f}%` profit  ·  `{win_rate:.1f}%` win rate",
            inline=False
        )
    embed.set_footer(text="BacktestingMax  •  Daily Challenge Results")
    return embed


def error_embed(message):
    return discord.Embed(
        title="⚠️  Something went wrong",
        description=f"```{message}```",
        color=RED
    ).set_footer(text="BacktestingMax  •  Error")