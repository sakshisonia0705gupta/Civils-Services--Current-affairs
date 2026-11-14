
import json
import re
import urllib.request
import xml.etree.ElementTree as ET
from html import unescape
from pathlib import Path

RSS_URL = (
    "https://pib.gov.in/RssMain.aspx"
    "?ModId=6&Lang=1&Regid=1"
)

def local_name(tag):
    return tag.rsplit("}", 1)[-1].lower()

def get_text(element, names):
    for child in element:
        if local_name(child.tag) in names:
            return "".join(child.itertext()).strip()
    return ""

def clean_text(value):
    value = unescape(value)
    value = re.sub(r"<[^>]+>", " ", value)
    return re.sub(r"\s+", " ", value).strip()

def fetch_pib_news():
    request = urllib.request.Request(
        RSS_URL,
        headers={"User-Agent": "Mozilla/5.0 UPSC-Intelligence-Hub"}
    )

    with urllib.request.urlopen(request, timeout=40) as response:
        xml_data = response.read()

    root = ET.fromstring(xml_data)

    entries = [
        element for element in root.iter()
        if local_name(element.tag) in ("item", "entry")
    ]

    print("Feed entries found:", len(entries))

    news_items = []

    for item in entries:
        title = get_text(item, {"title"})
        link = get_text(item, {"link"})

        if not link:
            for element in item:
                if local_name(element.tag) == "link":
                    link = element.attrib.get("href", "").strip()
                    if link:
                        break

        description = (
            get_text(item, {"description"})
            or get_text(item, {"summary"})
            or get_text(item, {"content"})
        )

        pub_date = (
            get_text(item, {"pubdate"})
            or get_text(item, {"published"})
            or get_text(item, {"updated"})
        )

        if not title or not link:
            continue

        news_items.append({
            "id": link,
            "date": pub_date,
            "source": "PIB",
            "category": "Miscellaneous",
            "title": clean_text(title),
            "summary": clean_text(description),
            "prelims_facts": [],
            "mains_analysis": "",
            "source_url": link,
            "is_sample": False
        })

    if not news_items:
        raise RuntimeError(
            "No PIB articles found. Check the feed response and XML format."
        )

    output = Path("data/news.json")
    output.parent.mkdir(parents=True, exist_ok=True)

    output.write_text(
        json.dumps(news_items, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )

    print("Successfully collected", len(news_items), "PIB articles.")

if __name__ == "__main__":
    fetch_pib_news()
