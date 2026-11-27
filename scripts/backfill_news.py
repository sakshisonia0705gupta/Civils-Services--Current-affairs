
import json
import re
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, date, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path

START_DATE = date(2026, 4, 1)
END_DATE = date.today()

PREVIEW = Path("data/backfill_preview.json")
REPORT = Path("data/backfill_report.json")

HEADERS = {
    "User-Agent": "UPSC-Intelligence-Hub/1.0"
}
TIMEOUT = 30

# Only sources useful for UPSC preparation.
SOURCES = [
    ("PIB", "https://pib.gov.in/RssMain.aspx?ModId=6&Lang=1&Regid=1"),
    ("The Hindu", "https://www.thehindu.com/news/national/?service=rss"),
    ("Indian Express UPSC", "https://indianexpress.com/section/upsc-current-affairs/feed/"),
    ("Indian Express Economy", "https://indianexpress.com/section/business/economy/feed/"),
    ("Indian Express Explained", "https://indianexpress.com/section/explained/feed/"),
    ("RBI Press Releases", "https://rbi.org.in/pressreleases_rss.xml"),
    ("RBI Notifications", "https://rbi.org.in/notifications_rss.xml"),
]

# Broad syllabus-linked themes. These are screening signals,
# not a claim that every matching article is automatically useful.
TOPICS = {
    "Polity & Governance": r"constitution|constitutional|supreme court|high court|judgment|judgement|parliament|bill|act\b|fundamental rights|federalism|election commission|governance|civil service|lokpal|data protection",
    "Economy": r"rbi|reserve bank|repo rate|monetary policy|inflation|gdp|fiscal|budget|gst|tax|banking|financial inclusion|employment|poverty|exports|imports|trade|economic survey|sebi",
    "International Relations": r"bilateral|diplomatic|foreign policy|united nations|wto|g20|brics|quad|indo.pacific|treaty|summit|international cooperation",
    "Environment": r"climate|biodiversity|wildlife|forest|wetland|ramsar|pollution|renewable energy|ecosystem|species|national park|conservation|sustainability",
    "Science & Technology": r"isro|space mission|satellite|artificial intelligence|quantum|semiconductor|biotechnology|genome|research|innovation|nuclear energy|digital technology",
    "Defence & Internal Security": r"armed forces|military exercise|border security|cyber security|cybersecurity|internal security|coast guard|defence production",
    "Agriculture": r"agriculture|farmer|minimum support price|msp\b|crop|irrigation|food security|fertilizer|fisheries|animal husbandry",
    "Society & Social Justice": r"public health|healthcare|nutrition|education|literacy|women empowerment|child welfare|social justice|tribal|sanitation|drinking water|disability",
    "History, Art & Culture": r"heritage|archaeology|unesco|museum|festival|traditional craft|handicraft|artisan|classical language|monument",
    "Reports & Institutions": r"report|index|ranking|census|survey|committee|commission|cag\b|statistics|parliamentary committee",
    "Disaster Management": r"disaster management|flood|drought|cyclone|earthquake|heatwave|early warning",
}

# A topic match is required. These cues help identify
# developments with stronger policy or institutional significance.
IMPORTANT_CUES = re.compile(
    r"new policy|policy framework|scheme|mission|programme|"
    r"program|guidelines|reform|regulation|report|index|"
    r"agreement|treaty|judgment|act\b|bill\b|"
    r"launch|approved|inaugurated|data release|"
    r"conservation|research findings|monetary policy",
    re.I
)

def local_name(tag):
    return tag.split("}")[-1].lower()

def child_text(element, names):
    for child in element.iter():
        if local_name(child.tag) in names and child.text:
            return child.text.strip()
    return ""

def entry_link(element):
    for child in element:
        if local_name(child.tag) == "link":
            link = child.attrib.get("href") or child.text
            if link:
                return link.strip()
    return ""

def parse_date(value):
    if not value:
        return None
    try:
        return parsedate_to_datetime(value).date()
    except Exception:
        pass
    try:
        return datetime.fromisoformat(
            value.replace("Z", "+00:00")
        ).date()
    except Exception:
        return None

def classify(title, description):
    text = (title + " " + description).lower()
    matches = [
        topic for topic, pattern in TOPICS.items()
        if re.search(pattern, text, re.I)
    ]
    return matches

def assess(title, description):
    topics = classify(title, description)
    text = title + " " + description

    if not topics:
        return None

    # Retain topic matches for human review, while giving
    # stronger priority to developments with policy cues.
    priority = (
        "High" if IMPORTANT_CUES.search(text)
        else "Review"
    )
    return topics, priority

def fetch_source(name, url):
    request = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
        root = ET.fromstring(response.read())

    records = []
    for entry in root.iter():
        if local_name(entry.tag) not in ("item", "entry"):
            continue

        title = child_text(entry, {"title"})
        link = entry_link(entry)
        description = child_text(
            entry, {"description", "summary"}
        )
        published = child_text(
            entry, {"pubdate", "published", "updated", "date"}
        )
        article_date = parse_date(published)

        if not title or not link or not article_date:
            continue
        if not link.startswith("https://"):
            continue
        if not START_DATE <= article_date <= END_DATE:
            continue

        result = assess(title, description)
        if not result:
            continue

        topics, priority = result
        records.append({
            "title": title,
            "date": article_date.isoformat(),
            "month": article_date.strftime("%Y-%m"),
            "source": name,
            "source_url": link,
            "upsc_subjects": topics,
            "priority": priority,
            "review_status": "human_review_required",
            "notes_status": "not_prepared"
        })

    return records

def main():
    all_records = []
    source_report = []

    for name, url in SOURCES:
        try:
            records = fetch_source(name, url)
            all_records.extend(records)
            source_report.append({
                "source": name,
                "status": "checked",
                "upsc_candidates": len(records)
            })
            print(name, ":", len(records), "UPSC candidates")
        except Exception as error:
            source_report.append({
                "source": name,
                "status": "failed",
                "error": str(error)[:250]
            })
            print(name, "FAILED:", str(error)[:150])

    # Deduplicate identical original links.
    unique = {}
    for item in all_records:
        key = item["source_url"].rstrip("/")
        if key not in unique:
            unique[key] = item

    records = sorted(
        unique.values(),
        key=lambda item: (item["date"], item["title"].lower()),
        reverse=True
    )

    month_counts = {}
    current = date(2026, 4, 1)
    while current <= END_DATE:
        key = current.strftime("%Y-%m")
        month_counts[key] = sum(
            1 for item in records if item["month"] == key
        )
        if current.month == 12:
            current = date(current.year + 1, 1, 1)
        else:
            current = date(current.year, current.month + 1, 1)

    report = {
        "period_start": START_DATE.isoformat(),
        "period_end": END_DATE.isoformat(),
        "run_date_utc": datetime.now(timezone.utc).isoformat(),
        "upsc_candidates": len(records),
        "monthly_candidate_counts": month_counts,
        "sources": source_report,
        "limitations": [
            "This run checks RSS feeds, not the complete PIB archive.",
            "RSS feeds may not contain all historical releases.",
            "A topic match is only a screening result, not final UPSC relevance.",
            "Every candidate requires content review before becoming study material.",
            "No AI-generated notes are claimed or created by this script."
        ],
        "live_news_json_modified": False
    }

    PREVIEW.parent.mkdir(parents=True, exist_ok=True)
    PREVIEW.write_text(
        json.dumps(records, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )
    REPORT.write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )

    print("\nDiagnostic completed.")
    print("UPSC candidates:", len(records))
    print("Preview:", PREVIEW)
    print("Report:", REPORT)
    print("Existing news.json was NOT changed.")

if __name__ == "__main__":
    main()
