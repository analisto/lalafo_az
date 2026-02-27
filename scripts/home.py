import asyncio
import aiohttp
import csv
import os
import ssl

BASE_URL = "https://lalafo.az/api/search/v3/feed/search"

PARAMS_BASE = {
    "category_id": 1423,
    "expand": "url",
    "per-page": 20,
    "with_feed_banner": "true",
}

HEADERS = {
    "accept": "application/json, text/plain, */*",
    "accept-language": "en-GB,en-US;q=0.9,en;q=0.8,ru;q=0.7,az;q=0.6",
    "country-id": "13",
    "device": "pc",
    "dnt": "1",
    "language": "az_AZ",
    "referer": "https://lalafo.az/azerbaijan/dom-i-sad",
    "sec-ch-ua": '"Not:A-Brand";v="99", "Google Chrome";v="145", "Chromium";v="145"',
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": '"Windows"',
    "sec-fetch-dest": "empty",
    "sec-fetch-mode": "cors",
    "sec-fetch-site": "same-origin",
    "user-agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/145.0.0.0 Safari/537.36"
    ),
}

CSV_FIELDS = [
    "id",
    "title",
    "price",
    "currency",
    "city",
    "views",
    "is_vip",
    "is_premium",
    "url",
    "created_time",
    "updated_time",
    "category_id",
    "user_id",
    "images_count",
    "description",
]

OUTPUT_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "home.csv")

CONCURRENCY = 5


def parse_items(data: dict) -> list[dict]:
    rows = []
    for item in data.get("items", []):
        if not item.get("id"):
            continue
        city = item.get("city", "")
        if isinstance(city, dict):
            city = city.get("name", "")
        images = item.get("images") or []
        rows.append({
            "id": item.get("id"),
            "title": item.get("title", ""),
            "price": item.get("price", ""),
            "currency": item.get("currency", ""),
            "city": city,
            "views": item.get("views", ""),
            "is_vip": item.get("is_vip", False),
            "is_premium": item.get("is_premium", False),
            "url": item.get("url", ""),
            "created_time": item.get("created_time", ""),
            "updated_time": item.get("updated_time", ""),
            "category_id": item.get("category_id", ""),
            "user_id": item.get("user_id", ""),
            "images_count": len(images),
            "description": (item.get("description") or "").replace("\n", " ").strip(),
        })
    return rows


async def fetch_page(session: aiohttp.ClientSession, page: int) -> dict:
    params = {**PARAMS_BASE, "page": page}
    async with session.get(BASE_URL, params=params, headers=HEADERS) as resp:
        resp.raise_for_status()
        return await resp.json(content_type=None)


async def scrape(max_pages: int = 9999) -> None:
    os.makedirs(os.path.dirname(os.path.abspath(OUTPUT_PATH)), exist_ok=True)

    ssl_ctx = ssl.create_default_context()
    ssl_ctx.check_hostname = False
    ssl_ctx.verify_mode = ssl.CERT_NONE
    connector = aiohttp.TCPConnector(ssl=ssl_ctx)

    semaphore = asyncio.Semaphore(CONCURRENCY)
    total = 0

    async def bounded_fetch(page: int) -> tuple[int, dict | None]:
        async with semaphore:
            try:
                data = await fetch_page(session, page)
                return page, data
            except aiohttp.ClientResponseError as e:
                print(f"  [page {page}] HTTP {e.status}: {e.message}")
                return page, None
            except Exception as e:
                print(f"  [page {page}] Error: {e}")
                return page, None

    async with aiohttp.ClientSession(connector=connector) as session:
        print("Fetching page 1 to discover total pages...")
        first_data = await fetch_page(session, 1)
        meta = first_data.get("_meta", {})
        total_pages = int(meta.get("pageCount", 1))
        total_count = int(meta.get("totalCount", 0))
        pages_to_fetch = min(max_pages, total_pages)
        print(f"Total listings: {total_count} across {total_pages} pages. Fetching {pages_to_fetch} pages.\n")

        with open(OUTPUT_PATH, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=CSV_FIELDS)
            writer.writeheader()

            rows = parse_items(first_data)
            writer.writerows(rows)
            f.flush()
            total += len(rows)
            print(f"Page  1/{pages_to_fetch}: {len(rows)} listings (total: {total})")

            remaining = list(range(2, pages_to_fetch + 1))
            for batch_start in range(0, len(remaining), CONCURRENCY * 2):
                batch = remaining[batch_start: batch_start + CONCURRENCY * 2]
                results = await asyncio.gather(*[bounded_fetch(p) for p in batch])

                for page, data in sorted(results, key=lambda x: x[0]):
                    if data is None:
                        continue
                    rows = parse_items(data)
                    if not rows:
                        print(f"Page {page:3}/{pages_to_fetch}: no items, skipping.")
                        continue
                    writer.writerows(rows)
                    f.flush()
                    total += len(rows)
                    print(f"Page {page:3}/{pages_to_fetch}: {len(rows)} listings (total: {total})")

    print(f"\nDone. Saved {total} listings -> {os.path.abspath(OUTPUT_PATH)}")


if __name__ == "__main__":
    asyncio.run(scrape())
