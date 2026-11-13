
import json
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path

RSS_URL = (
    "https://pib.gov.in/RssMain.aspx"
    "?ModId=6&Lang=1&Regid=1"
)

def fetch_pib_news():
    request = urllib.request.Request(
        RSS_URL,
        headers={"User-Agent": "UPSC-Intelligence-Hub/1.0"}
    )

    with urllib.request.urlopen(request, timeout=30) as response:
        xml_data = response.read()

    root = ET.fromstring(xml_data)
    news_items = []

    for item in root.findall(".//item"):
        title = item.findtext("title", "").strip()
        link = item.findtext("link", "").strip()
        description = item.findtext("description", "").strip()
        pub_date = item.findtext("pubDate", "").strip()

        if not title or not link:
            continue

        news_items.append({
            "id": link,
            "date": pub_date,
            "source": "PIB",
            "category": "Miscellaneous",
            "title": title,
            "summary": description,
            "prelims_facts": [],
            "mains_analysis": "",
            "source_url": link,
            "is_sample": False
        })

    output = Path("data/news.json")
    output.parent.mkdir(parents=True, exist_ok=True)

    output.write_text(
        json.dumps(news_items, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )

    print(f"Successfully collected {len(news_items)} PIB items.")

if __name__ == "__main__":
    fetch_pib_news()

