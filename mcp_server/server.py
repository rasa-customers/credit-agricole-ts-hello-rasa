"""
FastMCP server exposing generic banking data tools for the Crédit Agricole Rasa bot.

Tools
-----
get_user        — full profile for a bank client
get_cards       — filterable card query for a client
get_payments    — filterable + aggregatable transaction query for a client

Data comes from pre-filtered Parquet files (run prepare_data.py first).

Usage
-----
    python mcp_server/server.py

Server listens on http://0.0.0.0:8000 (streamable-http transport, path /mcp).
"""

import json
import logging
from datetime import date
from pathlib import Path
from typing import Optional

import duckdb
import pandas as pd
from dateutil.relativedelta import relativedelta
from fastmcp import FastMCP
from starlette.requests import Request
from starlette.responses import JSONResponse

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).parent / "data"
CARDS_PARQUET = str(DATA_DIR / "cards_demo.parquet")
TRANSACTIONS_PARQUET = str(DATA_DIR / "transactions_demo.parquet")

mcp = FastMCP(
    name="credit-agricole-mcp",
    instructions=(
        "Tools for querying bank client data (cards, transactions, user profile). "
        "Always pass the client_id or user_id from the conversation context. "
        "For ranking/aggregation questions use get_payments with group_by."
    ),
)


# ── Load static datasets once at startup ─────────────────────────────────────

logger.info("Loading demo datasets…")
CARDS_DF = pd.read_parquet(DATA_DIR / "cards_demo.parquet")
USERS_DF = pd.read_parquet(DATA_DIR / "users_demo.parquet")

with open(DATA_DIR / "mcc_codes.json") as fh:
    MCC_CODES: dict[str, str] = json.load(fh)


def _parse_expiry(value: str) -> date:
    """Parse 'MM/YYYY' into the last calendar day of that month."""
    month, year = str(value).strip().split("/")
    first_of_next = date(int(year), int(month), 1) + relativedelta(months=1)
    return first_of_next - relativedelta(days=1)


CARDS_DF["expiry_date"] = CARDS_DF["expires"].apply(_parse_expiry)
logger.info(f"Ready — {len(CARDS_DF)} cards, {len(USERS_DF)} users")


# ── Tools ─────────────────────────────────────────────────────────────────────


@mcp.tool()
def get_user(user_id: int) -> str:
    """Return the full profile of a bank client.

    Args:
        user_id: The client's unique ID (use the mcp_client_id from context).

    Returns:
        JSON object with: current_age, gender, address, latitude, longitude,
        per_capita_income, yearly_income, total_debt, credit_score,
        num_credit_cards.
    """
    row = USERS_DF[USERS_DF["id"] == user_id]
    if row.empty:
        return json.dumps(
            {"error": f"No user found with id {user_id}."},
            ensure_ascii=False,
        )
    return json.dumps(row.iloc[0].to_dict(), ensure_ascii=False, default=str)


@mcp.tool()
def get_cards(
    client_id: int,
    card_brand: Optional[str] = None,
    card_type: Optional[str] = None,
    active_only: bool = False,
    has_chip: Optional[str] = None,
    card_on_dark_web: Optional[str] = None,
) -> str:
    """Query a client's bank cards with optional filters.

    Available card brands: Visa, Mastercard, Discover.
    Available card types: Debit, Credit, Debit (Prepaid).

    Args:
        client_id:        The client's unique ID (use the mcp_client_id from context).
        card_brand:       Filter by brand — "Visa", "Mastercard", or "Discover".
        card_type:        Filter by type — "Debit", "Credit", or "Debit (Prepaid)".
        active_only:      If True, return only cards that have not yet expired.
        has_chip:         Filter by chip presence — "YES" or "NO".
        card_on_dark_web: Filter by dark-web flag — "Yes" or "No".

    Returns:
        JSON with total count and a list of cards. Each card includes:
        card_id, brand, type, last4 digits, expires, credit_limit,
        has_chip, card_on_dark_web, is_active.
    """
    today = date.today()
    df = CARDS_DF[CARDS_DF["client_id"] == client_id].copy()

    if df.empty:
        return json.dumps(
            {"error": f"No cards found for client {client_id}."},
            ensure_ascii=False,
        )

    if card_brand:
        df = df[df["card_brand"].str.lower() == card_brand.lower()]
    if card_type:
        df = df[df["card_type"].str.lower() == card_type.lower()]
    if has_chip:
        df = df[df["has_chip"].str.upper() == has_chip.upper()]
    if card_on_dark_web:
        df = df[df["card_on_dark_web"].str.lower() == card_on_dark_web.lower()]
    if active_only:
        df = df[df["expiry_date"] >= today]

    cards = [
        {
            "card_id": int(row["id"]),
            "brand": row["card_brand"],
            "type": row["card_type"],
            "last4": str(row["card_number"])[-4:],
            "expires": row["expires"],
            "credit_limit": row["credit_limit"],
            "credit_limit_num": float(row["credit_limit_num"]),
            "has_chip": row["has_chip"],
            "card_on_dark_web": row["card_on_dark_web"],
            "is_active": bool(row["expiry_date"] >= today),
        }
        for _, row in df.iterrows()
    ]

    return json.dumps({"total": len(cards), "cards": cards}, ensure_ascii=False, default=str)


@mcp.tool()
def get_payments(
    client_id: int,
    merchant_city: Optional[str] = None,
    merchant_state: Optional[str] = None,
    mcc_code: Optional[int] = None,
    amount_min: Optional[float] = None,
    amount_max: Optional[float] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    card_id: Optional[int] = None,
    group_by: Optional[str] = None,
    limit: int = 200,
) -> str:
    """Query payment transactions for a client with optional filters and aggregation.

    For ranking/summary questions (e.g. "top city", "most spent category",
    "spending per card"), use the group_by parameter — it returns counts and
    totals sorted by frequency. The limit parameter is ignored when group_by is set.

    group_by accepted values: "merchant_city", "merchant_state", "mcc",
                               "card_id", "use_chip".

    MCC codes are translated to category labels automatically
    (e.g. 5812 → "Eating Places and Restaurants", 5411 → "Grocery Stores").

    Args:
        client_id:       The client's unique ID (use the mcp_client_id from context).
        merchant_city:   Filter by city name (case-insensitive, partial match).
        merchant_state:  Filter by US state code, e.g. "CA", "NY".
        mcc_code:        Filter by Merchant Category Code (integer).
        amount_min:      Minimum transaction amount (can be negative for refunds).
        amount_max:      Maximum transaction amount.
        date_from:       Start date in YYYY-MM-DD format.
        date_to:         End date in YYYY-MM-DD format.
        card_id:         Filter by a specific card ID.
        group_by:        Column to aggregate by (see above). Returns count,
                         total_amount, avg_amount, first_date, last_date per group.
        limit:           Max raw transactions to return (default 200).

    Returns:
        JSON with total count and either grouped summaries or raw transactions
        (with mcc_label field added for human-readable category names).
    """
    VALID_GROUP_BY = {"merchant_city", "merchant_state", "mcc", "card_id", "use_chip"}

    con = duckdb.connect()
    try:
        # Build parameterised WHERE clause
        conditions = ["client_id = ?"]
        params: list = [client_id]

        if merchant_city:
            conditions.append("LOWER(merchant_city) LIKE LOWER(?)")
            params.append(f"%{merchant_city}%")
        if merchant_state:
            conditions.append("LOWER(merchant_state) = LOWER(?)")
            params.append(merchant_state)
        if mcc_code is not None:
            conditions.append("mcc = ?")
            params.append(mcc_code)
        if amount_min is not None:
            conditions.append("amount >= ?")
            params.append(amount_min)
        if amount_max is not None:
            conditions.append("amount <= ?")
            params.append(amount_max)
        if date_from:
            conditions.append("date >= ?")
            params.append(date_from)
        if date_to:
            conditions.append("date <= ?")
            params.append(f"{date_to} 23:59:59")
        if card_id is not None:
            conditions.append("card_id = ?")
            params.append(card_id)

        where = " AND ".join(conditions)

        if group_by and group_by in VALID_GROUP_BY:
            query = f"""
                SELECT
                    {group_by},
                    COUNT(*)    AS transaction_count,
                    SUM(amount) AS total_amount,
                    AVG(amount) AS avg_amount,
                    MIN(date)   AS first_date,
                    MAX(date)   AS last_date
                FROM read_parquet('{TRANSACTIONS_PARQUET}')
                WHERE {where}
                GROUP BY {group_by}
                ORDER BY transaction_count DESC
            """
            result = con.execute(query, params).fetchdf()

            if group_by == "mcc":
                result["category"] = (
                    result["mcc"].astype(str).map(lambda c: MCC_CODES.get(c, "Unknown"))
                )

            rows = result.to_dict(orient="records")
            return json.dumps(
                {"total_groups": len(rows), "group_by": group_by, "groups": rows},
                ensure_ascii=False,
                default=str,
            )

        else:
            # Count total matching rows
            count_q = f"SELECT COUNT(*) FROM read_parquet('{TRANSACTIONS_PARQUET}') WHERE {where}"
            total = con.execute(count_q, params).fetchone()[0]

            query = f"""
                SELECT
                    id, date, card_id, amount, use_chip,
                    merchant_city, merchant_state, mcc, errors
                FROM read_parquet('{TRANSACTIONS_PARQUET}')
                WHERE {where}
                ORDER BY date DESC
                LIMIT {int(limit)}
            """
            result = con.execute(query, params).fetchdf()
            rows = result.to_dict(orient="records")

            for row in rows:
                row["mcc_label"] = MCC_CODES.get(str(row.get("mcc") or ""), "Unknown")

            return json.dumps(
                {"total_matching": total, "returned": len(rows), "transactions": rows},
                ensure_ascii=False,
                default=str,
            )
    finally:
        con.close()


# ── REST endpoints ────────────────────────────────────────────────────────────


@mcp.custom_route("/user-profile", methods=["GET"])
async def user_profile(request: Request) -> JSONResponse:
    """Return the profile of a demo user.

    Query param: user_id (int)
    """
    try:
        user_id = int(request.query_params["user_id"])
    except (KeyError, ValueError):
        return JSONResponse({"success": False, "error": "Missing or invalid user_id"}, status_code=400)

    row = USERS_DF[USERS_DF["id"] == user_id]
    if row.empty:
        return JSONResponse({"success": False, "error": f"User {user_id} not found"}, status_code=404)

    profile = row.iloc[0].to_dict()
    return JSONResponse({"success": True, "profile": {k: str(v) for k, v in profile.items()}})


@mcp.custom_route("/update-address", methods=["POST"])
async def update_address(request: Request) -> JSONResponse:
    """Update the address of a demo user.

    Expected JSON body: {"user_id": int, "new_address": str}
    """
    global USERS_DF
    try:
        body = await request.json()
        user_id = int(body["user_id"])
        new_address = str(body["new_address"]).strip()

        if not new_address:
            return JSONResponse({"success": False, "error": "new_address is empty"}, status_code=400)

        if not (USERS_DF["id"] == user_id).any():
            return JSONResponse({"success": False, "error": f"User {user_id} not found"}, status_code=404)

        USERS_DF.loc[USERS_DF["id"] == user_id, "address"] = new_address
        USERS_DF.to_parquet(DATA_DIR / "users_demo.parquet", index=False)

        logger.info(f"Address updated for user {user_id}: {new_address}")
        return JSONResponse({"success": True, "user_id": user_id, "new_address": new_address})

    except (KeyError, ValueError) as e:
        return JSONResponse({"success": False, "error": str(e)}, status_code=400)


# ── Entrypoint ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    mcp.run(transport="streamable-http", host="0.0.0.0", port=8000)
