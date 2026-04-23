"""
BacktestingMax Mock API Server
MIT License — Copyright (c) 2026 Rishi Gopinath

Serves documented JSON schemas, enforces X-API-Key auth and 5s rate limit.
Run: uvicorn main:app --reload --port 8000
"""

import time
import random
from datetime import datetime, timedelta
from fastapi import FastAPI, Header, HTTPException, Query

app = FastAPI(title="BacktestingMax Mock API", version="1.0.0")

VALID_API_KEY = "mock-api-key-12345"
_last_request = 0.0

USERNAMES = [
    "AlphaTrader", "QuantKing", "MarketWizard", "ProfitHunter",
    "TrendSurfer", "BullRunner", "BearSlayer", "SwingMaster",
    "ScalpGod", "MomoTrader"
]
SYMBOLS = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "CADHKD", "EURUSD", "AAPL", "TSLA"]

def check(api_key: str):
    global _last_request
    if api_key != VALID_API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")
    now = time.time()
    if _last_request and (now - _last_request) < 5:
        raise HTTPException(
            status_code=429,
            headers={"Retry-After": "5"},
            detail="Rate limit: 1 request per 5 seconds"
        )
    _last_request = now

def mock_lb(date: str, limit: int):
    random.seed(date)
    entries = []
    for i, name in enumerate(USERNAMES[:limit]):
        entries.append({
            "rank": i + 1,
            "userId": f"user_{i+100}",
            "username": name,
            "profitPercent": round(random.uniform(-5, 40), 2),
            "winRate": round(random.uniform(40, 90), 1),
            "totalTrades": random.randint(5, 50),
            "subscriptionStatus": random.choice(["free", "free", "pro"])
        })
    entries.sort(key=lambda x: x["profitPercent"], reverse=True)
    for i, e in enumerate(entries):
        e["rank"] = i + 1
    return entries

@app.get("/daily_challenge")
def daily_challenge(x_api_key: str = Header(...)):
    check(x_api_key)
    today = datetime.utcnow()
    reset = datetime(today.year, today.month, today.day) + timedelta(days=1)
    random.seed(today.strftime("%Y-%m-%d"))
    return {
        "symbol": random.choice(SYMBOLS),
        "date": today.strftime("%Y-%m-%d"),
        "seconds_until_reset": int((reset - today).total_seconds())
    }

@app.get("/daily_challenge/leaderboard")
def leaderboard(
    date: str = Query(default=None),
    limit: int = Query(default=10, le=100),
    x_api_key: str = Header(...)
):
    check(x_api_key)
    return mock_lb(date or datetime.utcnow().strftime("%Y-%m-%d"), limit)

@app.get("/daily_challenge/lifetime")
def lifetime(x_api_key: str = Header(...)):
    check(x_api_key)
    users = []
    for i, name in enumerate(USERNAMES):
        random.seed(name)
        users.append({
            "rank": i + 1,
            "userId": f"user_{i+100}",
            "username": name,
            "totalDailyChallenges": random.randint(10, 300),
            "avgProfitPercent": round(random.uniform(2, 25), 2),
            "subscriptionStatus": random.choice(["free", "pro"])
        })
    users.sort(key=lambda x: x["totalDailyChallenges"], reverse=True)
    for i, u in enumerate(users):
        u["rank"] = i + 1
    return users

@app.get("/users/search")
def search(q: str = Query(...), x_api_key: str = Header(...)):
    check(x_api_key)
    return [
        {"userId": f"user_{i+100}", "username": name}
        for i, name in enumerate(USERNAMES)
        if q.lower() in name.lower()
    ]

@app.get("/users/{user_id}/daily_challenge_stats")
def user_stats(user_id: str, x_api_key: str = Header(...)):
    check(x_api_key)
    random.seed(user_id)
    return {
        "userId": user_id,
        "username": random.choice(USERNAMES),
        "completedChallenges": random.randint(20, 200),
        "avgProfitPercent": round(random.uniform(1, 30), 2),
        "bestProfitPercent": round(random.uniform(20, 80), 2),
        "winRate": round(random.uniform(40, 85), 1),
        "currentStreak": random.randint(0, 15),
        "placements": {
            "1": random.randint(0, 20),
            "2": random.randint(0, 15),
            "3": random.randint(0, 15),
            "top10": random.randint(10, 50)
        },
        "subscriptionStatus": random.choice(["free", "pro"])
    }
