"""
Prepare demo data for the MCP server.

Reads the raw CSV files and produces Parquet files filtered to 10 demo users,
so every query is exhaustive for those users without loading 13M rows in memory.

Run once (or whenever you want to refresh):

    python mcp_server/prepare_data.py
"""

from pathlib import Path

import duckdb
import pandas as pd

DATA_DIR = Path(__file__).parent / "data"


def main() -> None:
    # ── 1. Pick 10 demo users ─────────────────────────────────────────────────
    users_df = pd.read_csv(DATA_DIR / "users_data.csv")
    demo_users = users_df.head(10).copy()
    demo_user_ids = demo_users["id"].tolist()
    print(f"Demo user IDs: {demo_user_ids}")

    demo_users.to_parquet(DATA_DIR / "users_demo.parquet", index=False)
    print(f"✓ Saved {len(demo_users)} users → users_demo.parquet")

    # ── 2. Filter cards (6K rows — pandas is fast enough) ────────────────────
    cards_df = pd.read_csv(DATA_DIR / "cards_data.csv")
    # Normalise credit_limit: "$24,295" → 24295.0
    cards_df["credit_limit_num"] = (
        cards_df["credit_limit"]
        .str.replace("$", "", regex=False)
        .str.replace(",", "", regex=False)
        .astype(float)
    )
    cards_demo = cards_df[cards_df["client_id"].isin(demo_user_ids)].copy()
    cards_demo.to_parquet(DATA_DIR / "cards_demo.parquet", index=False)
    print(f"✓ Saved {len(cards_demo)} cards → cards_demo.parquet")

    # ── 3. Filter transactions via DuckDB (parallel scan of 1.2 GB CSV) ──────
    print("Filtering transactions — this may take a minute on first run…")
    ids_csv = ", ".join(str(i) for i in demo_user_ids)
    con = duckdb.connect()
    con.execute(f"""
        COPY (
            SELECT
                id,
                date,
                client_id,
                card_id,
                CAST(
                    REPLACE(REPLACE(amount, '$', ''), ',', '') AS DOUBLE
                )                                           AS amount,
                use_chip,
                merchant_id,
                merchant_city,
                merchant_state,
                zip,
                TRY_CAST(mcc AS INTEGER)                    AS mcc,
                errors
            FROM read_csv('{DATA_DIR}/transactions_data.csv', header=true, quote='"')
            WHERE client_id IN ({ids_csv})
        ) TO '{DATA_DIR}/transactions_demo.parquet' (FORMAT PARQUET)
    """)
    con.close()

    con2 = duckdb.connect()
    count = con2.execute(
        f"SELECT COUNT(*) FROM read_parquet('{DATA_DIR}/transactions_demo.parquet')"
    ).fetchone()[0]
    con2.close()
    print(f"✓ Saved {count:,} transactions → transactions_demo.parquet")
    print("\nData preparation complete!")


if __name__ == "__main__":
    main()
