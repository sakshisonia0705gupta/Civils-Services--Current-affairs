
import json
import re
import urllib.request
import xml.etree.ElementTree as ET

from datetime import datetime
from email.utils import parsedate_to_datetime
from html import unescape
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlparse, parse_qs


RSS_URL = (
    "https://pib.gov.in/RssMain.aspx"
    "?ModId=6&Lang=1&Regid=3&reg=3"
)

LISTING_URL = (
    "https://www.pib.gov.in/AllRelease.aspx"
    "?lang=1&reg=1"
)


class PIBListingParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.dates = {}
        self.current_id = ""
        self.after_link = False
        self.following_text = []

    def handle_starttag(self, tag, attrs):
        if tag.lower() == "a":
            self._finish_current()
            attrs = dict(attrs)
            href = attrs.get("href", "")
            release_id = get_release_id(href)

            if release_id:
                self.current_id = release_id
                self.after_link = False
                self.following_text = []

    def handle_endtag(self, tag):
        if tag.lower() == "a" and self.current_id:
            self.after_link = True

    def handle_data(self, data):
        if self.current_id and self.after_link:
            self.following_text.append(data)

    def _finish_current(self):
        if not self.current_id:
            return

        text = " ".join(self.following_text)

        match = re.search(
            r"Posted\s*on\s*:?\s*"
            r"(\d{1,2}\s+[A-Za-z]{3,9}\s*,?\s+\d{4})",
            text,
            re.IGNORECASE
        )

        if match:
            date_value = normalize_date(match.group(1))

            if date_value:
                self.dates[self.current_id] = date_value

        self.current_id = ""
        self.after_link = False
        self.following_text = []

    def close(self):
        super().close()
        self._finish_current()


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
        return parsedate_to_datetime(value).strftime("%Y-%m-%d")
    except (TypeError, ValueError, OverflowError):
        pass

    try:
        return datetime.fromisoformat(
            value.replace("Z", "+00:00")
        ).strftime("%Y-%m-%d")
    except ValueError:
        return ""


def get_release_id(url):
    try:
        query = parse_qs(urlparse(url).query)
        values = query.get("PRID") or query.get("prid")

        if values:
            return values[0]

    except Exception:
        pass

    match = re.search(
        r"[?&]PRID=(\d+)",
        url,
        re.IGNORECASE
    )

    return match.group(1) if match else ""


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
            candidate = "".join(element.itertext()).strip()
            result = normalize_date(candidate)

            if result:
                return result

    return ""


def get_listing_date_map():
    request = urllib.request.Request(
        LISTING_URL,
        headers={
            "User-Agent": "Mozilla/5.0 UPSC-Intelligence-Hub"
        }
    )

    with urllib.request.urlopen(request, timeout=40) as response:
        page = response.read().decode(
            "utf-8",
            errors="ignore"
        )

    parser = PIBListingParser()
    parser.feed(page)
    parser.close()

    print(
        "Official PIB listing dates indexed:",
        len(parser.dates)
    )

    return parser.dates


def get_posted_date(url):
    try:
        request = urllib.request.Request(
            url,
            headers={"User-Agent": "Mozilla/5.0"}
        )

        with urllib.request.urlopen(request, timeout=20) as response:
            page = response.read().decode(
                "utf-8",
                errors="ignore"
            )

        pattern = (
            r"Posted\s*On\s*:?\s*"
            r"(\d{1,2}\s+[A-Za-z]{3,9}\s*,?\s+\d{4})"
        )

        match = re.search(
            pattern,
            unescape(page),
            re.IGNORECASE
        )

        if match:
            return normalize_date(match.group(1))

    except Exception as error:
        print(
            "Date request failed:",
            type(error).__name__
        )

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

    try:
        listing_dates = get_listing_date_map()

    except Exception as error:
        print(
            "PIB listing date lookup failed:",
            type(error).__name__
        )
        listing_dates = {}

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

        pub_date = get_feed_date(item)

        if not pub_date:
            pub_date = listing_dates.get(
                get_release_id(link), ""
            )

        if not pub_date:
            pub_date = get_posted_date(link)

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
    output.parent.mkdir(
        parents=True,
        exist_ok=True
    )

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

    print(
        "Articles with usable dates:",
        dated_count
    )

    if news_items:
        print(
            "Example saved date:",
            news_items[0]["date"]
        )


if __name__ == "__main__":
    fetch_pib_news()
