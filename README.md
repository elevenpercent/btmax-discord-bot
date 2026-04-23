# BacktestingMax Discord Bot

> MIT Licensed · Built by [Rishi Gopinath](https://github.com/rishigopinath) · Open-Source Contribution for BacktestingMax

A production-grade Discord bot serving as the public interface for BacktestingMax's Daily Backtest Challenge. Built to institutional standards: fast, concurrency-safe, resilient, and visually polished.

---

## Features

| Command | Description |
|---|---|
| `/challenge` | Today's symbol, date, and countdown to reset |
| `/leaderboard [date]` | Top rankings with pagination (buttons + page-jump select menu) |
| `/lifetime` | All-time participation leaderboard |
| `/stats <username>` | Full user profile with placement histogram chart |
| Auto-post | Daily winner announcement at 00:05 UTC |

### Institutional Grade Standards
- **< 2s response** on all commands via `defer()` + aggressive caching
- **Concurrency-safe** async lock enforcing 1 req/5s rate limit
- **Resilient** — graceful 429 handling with `Retry-After` support + auto-retry on 5xx
- **Zero hardcoded secrets** — all config via `.env`
- **Structured logging** — latency tracking, cache hit/miss counters, error logging
- **Pro user differentiation** — `💎 PRO` badges throughout
- **Milestone achievements** — streak labels, century club, champion badges
- **Placement histograms** — quickchart.io bar charts in `/stats`

---

## Project Structure

```
btmax-discord-bot/
├── bot/
│   ├── bot.py          ← Main bot, slash commands, views
│   ├── api_client.py   ← Central HTTP client with queue, cache, retry
│   └── embeds.py       ← Pure embed builder functions + chart URLs
├── mock_server/
│   └── main.py         ← FastAPI mock API (dev/testing only)
├── .env.example        ← Config template
├── requirements.txt
├── LICENSE             ← MIT
└── README.md
```

---

## Setup

```bash
# 1. Clone and install
git clone https://github.com/yourusername/btmax-discord-bot
cd btmax-discord-bot
pip install -r requirements.txt

# 2. Configure
cp .env.example .env
# Edit .env — add your Discord bot token
```

---

## Running (Two Terminals)

**Terminal 1 — Mock Server (dev only):**
```bash
cd mock_server
uvicorn main:app --reload --port 8000
```

**Terminal 2 — Bot:**
```bash
cd bot
python bot.py
```

---

## Going to Production

Update `.env`:
```env
API_BASE_URL=https://backtestingmaxapi.onrender.com
API_KEY=your_production_key_here
```

No code changes required.

---

## Architecture

### API Client (`api_client.py`)
- Async lock serialises all outbound requests, enforcing the 5s global budget
- TTL cache: 5 min for live data, 24hr for historical leaderboards
- 429 handling: reads `Retry-After` header, waits, retries once
- Performance counters logged on shutdown: hits, misses, errors

### Caching TTLs
| Endpoint | TTL |
|---|---|
| `/daily_challenge` | 5 min |
| `/daily_challenge/leaderboard` (today) | 60 sec |
| `/daily_challenge/leaderboard` (past) | 24 hr |
| `/users/search` | 5 min |
| `/users/{id}/daily_challenge_stats` | 5 min |

---

## License

MIT © 2026 Rishi Gopinath — see [LICENSE](LICENSE)
