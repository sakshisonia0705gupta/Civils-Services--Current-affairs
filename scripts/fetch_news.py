
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


class PageText(HTMLParser):
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


def normalize_date(value):
    if not value:
        return ""

    value = unescape(value).strip()

    # Handles PIB: 14 NOV 2026 5:23PM
    match = re.search(
        r"(\d{1,2}\s+[A-Za-z]{3,9}\s*,?\s+\d{4})",
        value,
        re.IGNORECASE
    )

    if match:
        date_text = match.group(1).replace(",", "").strip()

        for fmt in ("%d %b %Y", "%d %B %Y"):
            try:
                return datetime.strptime(
                    date_text, fmt
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
            status = response.status

        # First inspect the page's visible text.
        parser = PageText()
        parser.feed(unescape(page))
        page_text = parser.get_text()

        pattern = (
            r"Posted\s*On\s*:?\s*"
            r"(\d{1,2}\s+[A-Za-z]{3,9}\s*,?\s+\d{4})"
        )

        match = re.search(
            pattern, page_text, re.IGNORECASE
        )

        if not match:
            # Also inspect the original HTML.
            match = re.search(
                pattern, unescape(page), re.IGNORECASE
            )

        if match:
            return normalize_date(match.group(1))

        # Diagnostic information, without printing article content.
        if url.endswith("2336232"):
            print("Diagnostic page status:", status)
            print("Diagnostic page length:", len(page))
            print(
                "Posted On found in response:",
                "Posted" in page or "Posted" in page_text
            )

        return ""

    except Exception as error:
        print("Date request failed:", type(error).__name__)
        return ""


def get_feed_date(item):
    date_fields = {
        "pubdate",
        "published",
        "updated",
        "date",
        "issued",
        "created"
    }

    for element in item.iter():
        if local_name(element.tag) in date_fields:
            candidate = "".join(
                element.itertext()
            ).strip()

            result = normalize_date(candidate)

            if result:
                return result

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

    print("Feed entries found:",  
    len(entries))
      if entries:
        print("PIB DATE DIAGNOSTIC:")
        for element in entries[0].iter():
            tag = local_name(element.tag)
            value = "".join(element.itertext()).strip()

            if any(word in tag for word in (
                "date", "time", "pub", "updated", "created"
            )):
                print("Field:", tag, "| Value:", value[:100])

            elif re.search(
                r"\d{1,2}\s+[A-Za-z]{3,9}\s*,?\s+\d{4}",
                value
            ):
                print("Possible date:", value[:100])

        print(
            "Parsed feed date:",
            get_feed_date(entries[0]) or "NOT FOUND"
             )
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

        if not title or not link:
            continue

        # Prefer the date supplied by the feed.
        pub_date = get_feed_date(item)

        # Check the original article page if needed.
        if not pub_date:
            pub_date = get_posted_date(link)

        # Store metadata and links only.
        # No publisher article text is copied.
        news_items.append({
            "id": link,
            "date": pub_date,
            "source": "PIB",
            "category": "Miscellaneous",
            "title": unescape(title).strip(),
            "summary": "",
            "prelims_facts": [],
            "mains_analysis": "",
            "source_url": link,
            "is_sample": False
        })

    if not news_items:
        raise RuntimeError(
            "No PIB articles found. Check the RSS feed."
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
        print(
            "Example saved date:",
            news_items[0]["date"]
        )


if __name__ == "__main__":
    fetch_pib_news()
