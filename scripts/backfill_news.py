
import json
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, date, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from urllib.parse import urlparse

START_DATE = date(2026, 4, 1)
END_DATE = date(2026, 11, 15)

PREVIEW_FILE = Path("data/backfill_preview.json")
REPORT_FILE = Path("data/backfill_report.json")

HEADERS = {
    "User-Agent": "UPSC-Current-Affairs-Hub/1.0 (personal study)"
}
TIMEOUT = 30

SOURCES = [
    {
        "name": "PIB",
        "url": "https://pib.gov.in/RssMain.aspx?ModId=6&Lang=1&Regid=1",
    },
    {
        "name": "The Hindu",
        "url": "http://www.thehindu.com/news/national/?service=rss",
    },
    {
        "name": "Indian Express UPSC",
        "url": "https://indianexpress.com/section/upsc-current-affairs/feed/",
    },
    {
        "name": "Indian Express Economy",
        "url": "https://indianexpress.com/section/business/economy/feed/",
    },
    {
        "name": "Indian Express Explained",
        "url": "https://indianexpress.com/section/explained/feed/",
    },
    {
        "name": "RBI Press Releases",
        "url": "https://rbi.org.in/pressreleases_rss.xml",
    },
    {
        "name": "RBI Notifications",
        "url": "https://rbi.org.in/notifications_rss.xml",
    },
    {
        "name": "RBI Speeches",
        "url": "https://rbi.org.in/speeches_rss.xml",
    },
]


def text_of(element, names):
    for child in element.iter():
        tag = child.tag.split("}")[-1].lower()
        if tag in names and child.text:
            return child.text.strip()
    return ""


def get_link(item):
    for child in item:
        tag = child.tag.split("}")[-1].lower()
        if tag == "link":
            href = child.attrib.get("href")
            if href:
                return href.strip()
            if child.text:
                return child.text.strip()
    return ""


def parse_date(value):
    if not value:
        return None

    try:
        parsed = parsedate_to_datetime(value)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.date()
    except Exception:
        pass

    try:
        return datetime.fromisoformat(
            value.replace("Z", "+00:00")
        ).date()
    except Exception:
        return None


def fetch_source(source):
    request = urllib.request.Request(
        source["url"], headers=HEADERS
    )

    with urllib.request.urlopen(
        request, timeout=TIMEOUT
    ) as response:
        raw = response.read()

    root = ET.fromstring(raw)
    records = []

    for item in root.iter():
        tag = item.tag.split("}")[-1].lower()

        if tag not in ("item", "entry"):
            continue

        title = text_of(item, {"title"})
        link = get_link(item)
        published = text_of(
            item,
            {"pubdate", "published", "updated", "date"}
        )

        article_date = parse_date(published)

        if not title or not link or not article_date:
            continue

        if not link.startswith(("http://", "https://")):
            continue

        if not urlparse(link).netloc:
            continue

        if START_DATE <= article_date <= END_DATE:
            records.append({
                "title": title,
                "date": article_date.isoformat(),
                "month": article_date.strftime("%Y-%m"),
                "source": source["name"],
                "source_url": link,
                "feed_url": source["url"],
                "review_status": "needs_content_review",
                "notes_status": "not_prepared",
            })

    return records


def main():
    all_records = []
    source_report = []

    for source in SOURCES:
        try:
            records = fetch_source(source)
            all_records.extend(records)

            source_report.append({
                "source": source["name"],
                "status": "checked",
                "candidate_count": len(records),
                "message": "Feed responded; historical coverage is not guaranteed."
            })

            print(
                source["name"],
                "—",
                len(records),
                "dated candidates"
            )

        except Exception as error:
            source_report.append({
                "source": source["name"],
                "status": "failed",
                "candidate_count": 0,
                "message": str(error)[:300]
            })

            print(source["name"], "— FAILED:", str(error)[:150])

    # Remove exact duplicate URLs.
    unique = {}
    for record in all_records:
        key = record["source_url"].rstrip("/")
        if key not in unique:
            unique[key] = record

    records = sorted(
        unique.values(),
        key=lambda item: (item["date"], item["title"].lower())
    )

    months = []
    year, month = 2026, 4

    while (year, month) <= (2026, 11):
        months.append(f"{year:04d}-{month:02d}")
        month += 1
        if month == 13:
            month = 1
            year += 1

    month_counts = {
        value: sum(
            1 for record in records
            if record["month"] == value
        )
        for value in months
    }

    report = {
        "period_start": START_DATE.isoformat(),
        "period_end": END_DATE.isoformat(),
        "run_date_utc": datetime.now(timezone.utc).isoformat(),
        "total_candidates": len(records),
        "duplicate_urls_removed": len(all_records) - len(records),
        "monthly_candidate_counts": month_counts,
        "sources": source_report,
        "important_warning": (
            "This is an RSS diagnostic, not proof of complete historical "
            "coverage. Zero results do not mean zero news existed. "
            "Full article review and archive-source checks are still required."
        )
    }

    PREVIEW_FILE.parent.mkdir(parents=True, exist_ok=True)

    PREVIEW_FILE.write_text(
        json.dumps(records, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )

    REPORT_FILE.write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )

    print("\nBackfill diagnostic finished.")
    print("Candidates:", len(records))
    print("Preview:", PREVIEW_FILE)
    print("Report:", REPORT_FILE)
    print("Live news archive was NOT changed.")


if __name__ == "__main__":
    main()
