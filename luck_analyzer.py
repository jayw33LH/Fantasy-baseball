import re
import time
import traceback
from datetime import datetime

import pandas as pd

_cache = {"batters": None, "pitchers": None, "timestamp": 0, "is_demo": False}
CACHE_TTL = 3600  # 1 hour


def get_luck_data(force_refresh=False):
    global _cache
    now = time.time()

    if (
        not force_refresh
        and _cache["batters"] is not None
        and (now - _cache["timestamp"]) < CACHE_TTL
    ):
        return {
            "batters": _cache["batters"],
            "pitchers": _cache["pitchers"],
            "last_updated": datetime.fromtimestamp(_cache["timestamp"]).isoformat(),
            "cached": True,
        }

    year = datetime.now().year

    try:
        import pybaseball

        pybaseball.cache.enable()

        batter_data = _fetch_batter_luck(pybaseball, year)
        pitcher_data = _fetch_pitcher_luck(pybaseball, year)

        # Fall back to demo data if live fetch returned nothing
        if not batter_data and not pitcher_data:
            return _load_demo_data("Live fetch returned empty results — showing demo data")

        _cache["batters"] = batter_data
        _cache["pitchers"] = pitcher_data
        _cache["timestamp"] = now
        _cache["is_demo"] = False

        return {
            "batters": batter_data,
            "pitchers": pitcher_data,
            "last_updated": datetime.now().isoformat(),
            "cached": False,
            "is_demo": False,
            "year": year,
        }
    except Exception as e:
        traceback.print_exc()
        return _load_demo_data(f"Could not reach Baseball Savant ({type(e).__name__}) — showing demo data")


def _load_demo_data(reason: str) -> dict:
    from demo_data import DEMO_BATTERS, DEMO_PITCHERS

    batters = sorted(DEMO_BATTERS, key=lambda p: p["luck_score"], reverse=True)
    pitchers = sorted(DEMO_PITCHERS, key=lambda p: p["luck_score"], reverse=True)

    now = time.time()
    _cache["batters"] = batters
    _cache["pitchers"] = pitchers
    _cache["timestamp"] = now
    _cache["is_demo"] = True

    return {
        "batters": batters,
        "pitchers": pitchers,
        "last_updated": datetime.now().isoformat(),
        "cached": False,
        "is_demo": True,
        "demo_reason": reason,
        "year": datetime.now().year,
    }


def _normalize_name(name: str) -> str:
    return re.sub(r"[^a-z ]", "", name.lower()).strip()


def find_player(name: str, players: list) -> dict | None:
    if not players:
        return None

    normalized = _normalize_name(name)

    # Build index on first call
    by_full = {}
    by_last = {}
    for p in players:
        pname = p.get("name", "")
        norm = _normalize_name(pname)
        by_full[norm] = p
        # "Last, First" format — last name is before the comma
        parts = pname.split(",")
        last_norm = _normalize_name(parts[0])
        if last_norm not in by_last:
            by_last[last_norm] = p

    # Exact match
    if normalized in by_full:
        return by_full[normalized]

    # "First Last" -> try "Last, First" style lookup
    parts = normalized.split()
    if len(parts) >= 2:
        # Try last-name-first lookup
        reversed_key = parts[-1]
        if reversed_key in by_last:
            return by_last[reversed_key]
        # Try "last first" form
        reversed_full = parts[-1] + " " + " ".join(parts[:-1])
        if reversed_full in by_full:
            return by_full[reversed_full]

    # Last name only
    if parts and parts[-1] in by_last:
        return by_last[parts[-1]]

    # Substring match
    for key, player in by_full.items():
        if normalized in key or key in normalized:
            return player

    return None


def _extract_name(df: pd.DataFrame) -> pd.Series:
    cols = [c.lower() for c in df.columns]
    df.columns = cols

    if "last_name, first_name" in cols:
        return df["last_name, first_name"]
    if "last_name" in cols and "first_name" in cols:
        return df["last_name"].str.strip() + ", " + df["first_name"].str.strip()

    name_cols = [c for c in cols if "name" in c]
    if name_cols:
        return df[name_cols[0]]

    return None


def _safe_float(val):
    try:
        f = float(val)
        return None if pd.isna(f) else f
    except Exception:
        return None


def _row_to_record(row, df_cols, extra_cols):
    record = {
        "name": str(row["name"]),
        "luck_score": round(_safe_float(row["luck_score"]) or 0, 3),
    }
    for col in extra_cols:
        if col in df_cols:
            val = _safe_float(row.get(col))
            if val is not None:
                record[col] = round(val, 3) if abs(val) < 10 else int(val)
    return record


def _fetch_batter_luck(pybaseball, year: int) -> list:
    try:
        df = pybaseball.statcast_batter_expected_stats(year, minPA=100)
        if df is None or df.empty:
            return []

        name_col = _extract_name(df)
        if name_col is None:
            return []
        df["name"] = name_col

        cols = list(df.columns)

        # Prefer pre-computed diff: est_woba_minus_woba_diff = xwOBA - wOBA
        # Luck for batter = wOBA - xwOBA, so negate the diff
        if "est_woba_minus_woba_diff" in cols:
            df["luck_score"] = -df["est_woba_minus_woba_diff"].astype(float)
        elif "woba" in cols and "est_woba" in cols:
            df["luck_score"] = df["woba"].astype(float) - df["est_woba"].astype(float)
        elif "ba" in cols and "est_ba" in cols:
            df["luck_score"] = df["ba"].astype(float) - df["est_ba"].astype(float)
        else:
            print(f"[batters] available columns: {cols}")
            return []

        # Rename est_woba -> xwoba for display
        if "est_woba" in cols and "xwoba" not in cols:
            df["xwoba"] = df["est_woba"]
        if "est_ba" in cols and "xba" not in cols:
            df["xba"] = df["est_ba"]

        df = df.sort_values("luck_score", ascending=False).reset_index(drop=True)
        extra = ["woba", "xwoba", "ba", "xba", "slg", "est_slg", "pa", "player_id"]
        return [_row_to_record(row, df.columns, extra) for _, row in df.iterrows()]

    except Exception:
        traceback.print_exc()
        return []


def _fetch_pitcher_luck(pybaseball, year: int) -> list:
    try:
        df = pybaseball.statcast_pitcher_expected_stats(year, minPA=100)
        if df is None or df.empty:
            return []

        name_col = _extract_name(df)
        if name_col is None:
            return []
        df["name"] = name_col

        cols = list(df.columns)

        # Lucky pitcher: ERA < xERA  → luck_score = xERA - ERA (positive = lucky)
        era_col = next((c for c in ["era", "p_era"] if c in cols), None)
        xera_col = "xera" if "xera" in cols else None

        if era_col and xera_col:
            df["luck_score"] = df[xera_col].astype(float) - df[era_col].astype(float)
            df["era"] = df[era_col]
        elif "est_woba_minus_woba_diff" in cols:
            # Pitcher perspective: xwOBA - wOBA allowed; positive = pitcher lucky
            df["luck_score"] = df["est_woba_minus_woba_diff"].astype(float)
        elif "woba" in cols and "est_woba" in cols:
            df["luck_score"] = df["est_woba"].astype(float) - df["woba"].astype(float)
        else:
            print(f"[pitchers] available columns: {cols}")
            return []

        if "est_woba" in cols and "xwoba" not in cols:
            df["xwoba"] = df["est_woba"]

        df = df.sort_values("luck_score", ascending=False).reset_index(drop=True)
        extra = ["era", "xera", "woba", "xwoba", "ba", "est_ba", "pa", "player_id"]
        return [_row_to_record(row, df.columns, extra) for _, row in df.iterrows()]

    except Exception:
        traceback.print_exc()
        return []
