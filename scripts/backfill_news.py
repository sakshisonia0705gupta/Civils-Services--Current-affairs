
import json
from pathlib import Path
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

URL = "https://www.pib.gov.in/AllRel.aspx?lang=1&reg=3"

PREVIEW = Path("data/backfill_preview.json")
REPORT = Path("data/backfill_report.json")

headers = {
    "User-Agent": "Mozilla/5.0"
}

session = requests.Session()

response = session.get(URL, headers=headers, timeout=45)
response.raise_for_status()

soup = BeautifulSoup(response.text, "html.parser")

releases = []

for a in soup.find_all("a", href=True):
    href = a["href"]

    if not any(x in href.lower() for x in [
        "pressreleasepage",
        "pressrelesedetail",
        "pressreleasedetail"
    ]):
        continue

    title = " ".join(a.get_text(" ", strip=True).split())

    if not title:
        continue

    releases.append({
        "title": title,
        "source": "PIB",
        "source_url": urljoin(URL, href)
    })

selects = []

for select in soup.find_all("select"):
    selects.append({
        "name": select.get("name"),
        "id": select.get("id"),
        "options": [
            option.get_text(" ", strip=True)
            for option in select.find_all("option")[:8]
        ]
    })

PREVIEW.parent.mkdir(parents=True, exist_ok=True)

PREVIEW.write_text(
    json.dumps(releases, ensure_ascii=False, indent=2),
    encoding="utf-8"
)

report = {
    "page_url": URL,
    "http_status": response.status_code,
    "page_title": soup.title.get_text(strip=True) if soup.title else "",
    "release_links_found": len(releases),
    "dropdowns_found": len(selects),
    "dropdown_details": selects,
    "sample_titles": [x["title"] for x in releases[:10]],
    "diagnostic_only": True,
    "live_news_json_modified": False
}

REPORT.write_text(
    json.dumps(report, ensure_ascii=False, indent=2),
    encoding="utf-8"
)

print("PIB PAGE DIAGNOSTIC FINISHED")
print("HTTP status:", response.status_code)
print("Release links found:", len(releases))
print("Dropdowns found:", len(selects))
print("Sample titles:")

for item in releases[:10]:
    print("-", item["title"])

print("Live news.json was NOT modified.")
