
import json
import re
import urllib.request
import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime
from datetime import datetime
from html import unescape
from pathlib import Path

RSS_URL = (
    "https://pib.gov.in/RssMain.aspx"
    "?ModId=6&Lang=1&Regid=3"
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


def normalize_date(value):
    if not value:
        return ""

    value = value.strip()

    try:
        return parsedate_to_datetime(value).strftime("%Y-%m-%d")
    except (TypeError, ValueError):
        pass

    for date_format in (
        "%d %B %Y",
        "%d %b %Y",
        "%Y-%m-%d",
    ):
        try:
            return datetime.strptime(
                value.replace(",", "").strip(),
                date_format
            ).strftime("%Y-%m-%d")
        except ValueError:
            continue

    return ""


def get_posted_date(url):
    try:
        request = urllib.request.Request(
            url,
            headers={"User-Agent": "Mozilla/5.0"}
        )

        with urllib.request.urlopen(request, timeout=12) as response:
            page = response.read().decode(
                "utf-8",
                errors="ignore"
            )

        match = re.search(
            r"Posted\s*On\s*:?\s*"
            r"(\d{1,2}\s+[A-Za-z]+\s*,?\s+\d{4})",
            page,
            re.IGNORECASE
        )

        if match:
            return normalize_date(match.group(1))

    except Exception as error:
        print("Could not read article date:", error)

    return ""


def fetch_pib_news():
    request = urllib.request.Request(
        RSS_URL,
        headers={
            "User-Agent": "Mozilla/5.0 UPSC-Intelligence-Hub"
        }
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

        # First try the actual publication date on the PIB article.
        pub_date = ""

        if link:
            pub_date = get_posted_date(link)

        # If the article page date is unavailable, use the RSS date.
        if not pub_date:
            for element in item.iter():
                if local_name(element.tag) in {
                    "pubdate",
                    "published",
                    "updated",
                    "date",
                    "issued",
                    "created"
                }:
                    candidate = "".join(
                        element.itertext()
                    ).strip()

                    if candidate:
                        pub_date = normalize_date(candidate)
                        if pub_date:
                            break

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
            "No PIB articles found. Check the feed response "
            "and XML format."
        )

    output = Path("data/news.json")
    output.parent.mkdir(parents=True, exist_ok=True)

    output.write_text(
        json.dumps(news_items, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )

    dated_count = sum(
        1 for item in news_items if item["date"]
    )

    print(
        "Successfully collected",
        len(news_items),
        "PIB articles."
    )
    print("Articles with usable dates:", dated_count)


if __name__ == "__main__":
    fetch_pib_news()
