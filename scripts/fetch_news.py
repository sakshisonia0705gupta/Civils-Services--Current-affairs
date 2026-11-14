
import json
import re
import urllib.request
import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime
from datetime import datetime
from html import unescape
from html.parser import HTMLParser
from pathlib import Path

RSS_URL = (
    "https://pib.gov.in/RssMain.aspx"
    "?ModId=6&Lang=1&Regid=3"
)


class TextExtractor(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts = []

    def handle_data(self, data):
        self.parts.append(data)

    def get_text(self):
        return " ".join(self.parts)


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

    value = unescape(value).strip()

    # PIB format: 14 NOV 2026 5:23PM
    match = re.search(
        r"(\d{1,2}\s+[A-Za-z]{3,9}\s*,?\s+\d{4})",
        value,
        re.IGNORECASE
    )

    if match:
        value = match.group(1).replace(",", "").strip()

        for fmt in ("%d %b %Y", "%d %B %Y"):
            try:
                return datetime.strptime(
                    value, fmt
                ).strftime("%Y-%m-%d")
            except ValueError:
                pass

    try:
        return parsedate_to_datetime(
            value
        ).strftime("%Y-%m-%d")
    except (TypeError, ValueError):
        pass

    try:
        return datetime.fromisoformat(
            value.replace("Z", "+00:00")
        ).strftime("%Y-%m-%d")
    except ValueError:
        pass

    return ""


def get_posted_date(url):
    try:
        request = urllib.request.Request(
            url,
            headers={"User-Agent": "Mozilla/5.0"}
        )

        with urllib.request.urlopen(
            request, timeout=20
        ) as response:
            page = response.read().decode(
                "utf-8", errors="ignore"
            )

        parser = TextExtractor()
        parser.feed(page)
        page_text = unescape(parser.get_text())

        match = re.search(
            r"Posted\s*On\s*:?\s*"
            r"(\d{1,2}\s+[A-Za-z]{3,9}\s*,?\s+\d{4})",
            page_text,
            re.IGNORECASE
        )

        if match:
            return normalize_date(match.group(1))

        # Try the original HTML if the date is inside metadata.
        match = re.search(
            r"Posted\s*On\s*:?\s*"
            r"(\d{1,2}\s+[A-Za-z]{3,9}\s*,?\s+\d{4})",
            unescape(page),
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

    with urllib.request.urlopen(
        request, timeout=40
    ) as response:
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
                    link = element.attrib.get(
                        "href", ""
                    ).strip()
                    if link:
                        break

        description = (
            get_text(item, {"description"})
            or get_text(item, {"summary"})
            or get_text(item, {"content"})
        )

        if not title or not link:
            continue

        pub_date = get_posted_date(link)

        # Use the feed date if the article page date is unavailable.
        if not pub_date:
            for element in item.iter():
                if local_name(element.tag) in {
                    "pubdate", "published", "updated",
                    "date", "issued", "created"
                }:
                    candidate = "".join(
                        element.itertext()
                    ).strip()

                    pub_date = normalize_date(candidate)

                    if pub_date:
                        break

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
            "No PIB articles found. Check the feed."
        )

    output = Path("data/news.json")
    output.parent.mkdir(parents=True, exist_ok=True)

    output.write_text(
        json.dumps(
            news_items,
            ensure_ascii=False,
            indent=2
        ),
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

    if news_items:
        print("Example saved date:", news_items[0]["date"])


if __name__ == "__main__":
    fetch_pib_news()
