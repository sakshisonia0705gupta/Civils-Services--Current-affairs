
import json
import re
import urllib.request
import xml.etree.ElementTree as ET

from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from html import unescape
from pathlib import Path
from urllib.parse import urlparse


# ============================================================
# UPSC CURRENT AFFAIRS HUB — MULTI-SOURCE COLLECTOR
# Version 1: RSS collection + archive preservation
# ============================================================

OUTPUT = Path("data/news.json")
TIMEOUT = 30
USER_AGENT = "UPSC-Current-Affairs-Hub/1.0 (personal study)"

# Only feeds listed here are automatically collected.
# Each feed is independently handled so one failure does
# not stop the other sources.

RSS_SOURCES = [
    {
        "name": "PIB",
        "url": (
            "https://pib.gov.in/RssMain.aspx"
            "?ModId=6&Lang=1&Regid=1"
        ),
    },
    {
        "name": "The Hindu",
        "url": (
            "http://www.thehindu.com/news/national/"
            "?service=rss"
        ),
    },
    {
        "name": "Indian Express - UPSC",
        "url": (
            "https://indianexpress.com/section/"
            "upsc-current-affairs/feed/"
        ),
    },
    {
        "name": "Indian Express - Economy",
        "url": (
            "https://indianexpress.com/section/"
            "business/economy/feed/"
        ),
    },
    {
        "name": "Indian Express - Explained",
        "url": (
            "https://indianexpress.com/section/"
            "explained/feed/"
        ),
    },
    {
        "name": "RBI - Press Releases",
        "url": "https://rbi.org.in/pressreleases_rss.xml",
    },
    {
        "name": "RBI - Notifications",
        "url": "https://rbi.org.in/notifications_rss.xml",
    },
    {
        "name": "RBI - Speeches",
        "url": "https://rbi.org.in/speeches_rss.xml",
    },
]


# These are important sources, but they are not yet
# connected to an automatically verified article feed.
# Do not treat this list as proof of automatic collection.

SOURCE_DIRECTORY = [
    {
        "name": "Economic Times",
        "type": "Newspaper",
        "url": "https://economictimes.indiatimes.com/",
        "status": "Manual source review - RSS reuse restricted",
    },
    {
        "name": "PRS India",
        "type": "Legislative research",
        "url": "https://prsindia.org/",
        "status": "Official website connector pending",
    },
    {
        "name": "Ministry of External Affairs",
        "type": "Government",
        "url": "https://www.mea.gov.in/",
        "status": "Official website connector pending",
    },
    {
        "name": "DRDO",
        "type": "Science and Defence",
        "url": "https://www.drdo.gov.in/",
        "status": "Official publication connector pending",
    },
    {
        "name": "ISRO",
        "type": "Science and Space",
        "url": "https://www.isro.gov.in/",
        "status": "Official website connector pending",
    },
    {
        "name": "Yojana",
        "type": "Government magazine",
        "url": "https://yojana.gov.in/",
        "status": "Magazine issue connector pending",
    },
    {
        "name": "Kurukshetra",
        "type": "Government magazine",
        "url": "https://yojana.gov.in/",
        "status": "Magazine issue connector pending",
    },
    {
        "name": "Down To Earth",
        "type": "Fortnightly magazine",
        "url": "https://www.downtoearth.org.in/",
        "status": "Magazine issue connector pending",
    },
    {
        "name": "Ministry of Environment",
        "type": "Government",
        "url": "https://moef.gov.in/",
        "status": "Official website connector pending",
    },
    {
        "name": "NITI Aayog",
        "type": "Government institution",
        "url": "https://www.niti.gov.in/",
        "status": "Official website connector pending",
    },
    {
        "name": "SEBI",
        "type": "Financial regulator",
        "url": "https://www.sebi.gov.in/",
        "status": "Official website connector pending",
    },
    {
        "name": "ICAR",
        "type": "Agriculture research",
        "url": "https://icar.org.in/",
        "status": "Official website connector pending",
    },
    {
        "name": "Ministry of Finance",
        "type": "Government",
        "url": "https://finmin.gov.in/",
        "status": "Official website connector pending",
    },
    {
        "name": "Ministry of Defence",
        "type": "Government",
        "url": "https://mod.gov.in/",
        "status": "Official website connector pending",
    },
]


# ============================================================
# UPSC CLASSIFICATION
# ============================================================

TOPICS = [
    (
        "Polity & Governance",
        r"constitution|constitutional|supreme court|high court|"
        r"judg(?:ment|ement)|bill|legislation|parliament|"
        r"lok sabha|rajya sabha|election commission|cag\b|"
        r"federalism|judiciary|tribunal|fundamental rights|"
        r"article 21|right to information|data protection|"
        r"governance|civil service|lokpal|administrative reform",
    ),
    (
        "Economy",
        r"\brbi\b|reserve bank|monetary policy|inflation|"
        r"\bgdp\b|fiscal|budget|\bgst\b|taxation|banking|"
        r"financial inclusion|foreign investment|\bfdi\b|"
        r"exports?|imports?|trade deficit|manufacturing|"
        r"employment|poverty|infrastructure|disinvestment|"
        r"\bsebi\b|economy|economic survey|currency",
    ),
    (
        "International Relations",
        r"treaty|bilateral|diplomatic|foreign policy|"
        r"united nations|\bwto\b|\bg20\b|\bbrics\b|"
        r"\bquad\b|indo.pacific|international cooperation|"
        r"multilateral|strategic partnership|summit|"
        r"foreign minister|international agreement",
    ),
    (
        "Defence & Security",
        r"defen[cs]e|armed forces|military|missile|"
        r"navy|air force|\barmy\b|border security|"
        r"cybersecurity|cyber security|internal security|"
        r"coast guard|\bdrdo\b|military exercise|"
        r"defence production",
    ),
    (
        "Science & Technology",
        r"\bisro\b|space mission|satellite|launch vehicle|"
        r"artificial intelligence|\bai\b|quantum|"
        r"semiconductor|biotechnology|genome|research|"
        r"innovation|nanotechnology|nuclear energy|"
        r"digital technology|supercomput|robotics",
    ),
    (
        "Environment",
        r"climate change|climate|biodiversity|wildlife|"
        r"forest conservation|wetland|ramsar|pollution|"
        r"renewable energy|solar energy|green hydrogen|"
        r"environment|ecosystem|species|national park|"
        r"tiger reserve|carbon emission|sustainab|"
        r"disaster management",
    ),
    (
        "Social Development",
        r"public health|healthcare|health|education|"
        r"literacy|nutrition|anganwadi|women empowerment|"
        r"gender|child welfare|social justice|tribal|"
        r"scheduled caste|scheduled tribe|disability|"
        r"sanitation|drinking water|migration|poverty",
    ),
    (
        "Agriculture",
        r"agricultur|farmer|minimum support price|\bmsp\b|"
        r"crop|irrigation|food security|food processing|"
        r"fertilizer|fisheries|animal husbandry|"
        r"rural development|agri.?stack",
    ),
    (
        "Reports & Institutions",
        r"national report|annual report|index\b|ranking|"
        r"survey\b|census\b|committee|commission|"
        r"working group|white paper|audit report|"
        r"statistics|data release|human development",
    ),
    (
        "Art, Culture & Heritage",
        r"heritage|archaeolog|unesco|museum|festival|"
        r"traditional craft|handicraft|artisan|"
        r"cultural diplomacy|intangible cultural|"
        r"literature|classical language|monument",
    ),
]


def classify_article(title, description=""):

    text = unescape(
        (title or "") + " " + (description or "")
    ).lower()

    for category, pattern in TOPICS:
        if re.search(pattern, text, re.IGNORECASE):
            return category

    return "General Current Affairs"


def assess_priority(title, description=""):

    text = (
        (title or "") + " " + (description or "")
    ).lower()

    high_cues = re.compile(
        r"supreme court|constitutional|union budget|"
        r"monetary policy|major reform|new act|"
        r"international treaty|national security|"
        r"major mission|climate agreement|"
        r"national policy|important judgment",
        re.IGNORECASE,
    )

    medium_cues = re.compile(
        r"report|index|scheme|programme|program|"
        r"notification|research|agreement|"
        r"international|technology|conservation|"
        r"agriculture|health|education|"
        r"committee|institution|heritage|"
        r"artisan|trade|development|"
        r"appointment|exercise|summit",
        re.IGNORECASE,
    )

    if high_cues.search(text):
        return "High", "Strong policy, constitutional or national significance."

    if medium_cues.search(text):
        return "Medium", "Potential syllabus connection; review its UPSC value."

    return "Low", "Retained for review; UPSC relevance needs assessment."


# ============================================================
# DATE HANDLING
# ============================================================

def normalize_date(value):

    if not value:
        return ""

    value = unescape(str(value)).strip()

    try:
        parsed = parsedate_to_datetime(value)
        return parsed.date().isoformat()
    except (TypeError, ValueError, OverflowError):
        pass

    try:
        return datetime.fromisoformat(
            value.replace("Z", "+00:00")
        ).date().isoformat()
    except ValueError:
        pass

    match = re.search(
        r"(\d{1,2}\s+[A-Za-z]{3,9}\s*,?\s+\d{4})",
        value,
        re.IGNORECASE,
    )

    if match:
        clean = match.group(1).replace(",", "").strip()

        for fmt in ("%d %b %Y", "%d %B %Y"):
            try:
                return datetime.strptime(
                    clean, fmt
                ).date().isoformat()
            except ValueError:
                pass

    return ""


def get_entry_date(entry):

    date_names = {
        "pubdate",
        "published",
        "updated",
        "date",
        "issued",
        "created",
    }

    for element in entry.iter():

        name = element.tag.rsplit("}", 1)[-1].lower()

        if name in date_names:
            result = normalize_date(
                "".join(element.itertext())
            )

            if result:
                return result

    return ""


# ============================================================
# RSS PARSING
# ============================================================

def fetch_url(url):

    request = urllib.request.Request(
        url,
        headers={"User-Agent": USER_AGENT},
    )

    with urllib.request.urlopen(
        request, timeout=TIMEOUT
    ) as response:

        return response.read()


def get_entry_link(entry):

    for element in entry.iter():

        if element.tag.rsplit("}", 1)[-1].lower() == "link":

            href = element.attrib.get("href", "").strip()

            if href:
                return href

            text = "".join(element.itertext()).strip()

            if text:
                return text

    return ""


def get_entry_text(entry, names):

    for element in entry.iter():

        name = element.tag.rsplit("}", 1)[-1].lower()

        if name in names:
            return "".join(element.itertext()).strip()

    return ""


def collect_feed(source):

    results = []

    try:
        xml_data = fetch_url(source["url"])
        root = ET.fromstring(xml_data)

        entries = [
            element
            for element in root.iter()
            if element.tag.rsplit("}", 1)[-1].lower()
            in ("item", "entry")
        ]

        for entry in entries:

            title = get_entry_text(entry, {"title"})
            link = get_entry_link(entry)

            if not title or not link:
                continue

            title = unescape(title).strip()

            description = get_entry_text(
                entry,
                {"description", "summary", "content"},
            )

            date_value = get_entry_date(entry)

            priority, reason = assess_priority(
                title, description
            )

            results.append({
                "id": link,
                "date": date_value,
                "source": source["name"],
                "category": classify_article(
                    title, description
                ),
                "title": title,
                "summary": "",
                "prelims_facts": [],
                "mains_analysis": "",
                "upsc_angle": {},
                "priority": priority,
                "priority_reason": reason,
                "source_url": link,
                "is_sample": False,
            })

        print(
            source["name"] + ":",
            len(results),
            "feed entries collected",
        )

    except Exception as error:

        print(
            source["name"] + " FAILED:",
            type(error).__name__,
            str(error)[:180],
        )

    return results


# ============================================================
# SAFE ARCHIVE MERGE
# ============================================================

def load_existing_archive():

    if not OUTPUT.exists():
        return []

    try:
        data = json.loads(
            OUTPUT.read_text(encoding="utf-8")
        )

        if not isinstance(data, list):
            raise ValueError("Archive is not a list.")

        return data

    except Exception as error:

        raise RuntimeError(
            "Existing news archive could not be read. "
            "Nothing has been overwritten."
        ) from error


def merge_archive(existing_items, new_items):

    merged = {}

    for article in existing_items:

        if not isinstance(article, dict):
            continue

        key = (
            article.get("source_url")
            or article.get("id")
        )

        if key:
            merged[key] = article

    added = 0
    refreshed = 0

    for article in new_items:

        key = (
            article.get("source_url")
            or article.get("id")
        )

        if not key:
            continue

        if key not in merged:

            merged[key] = article
            added += 1
            continue

        old = merged[key]

        # Update source metadata, but never erase
        # notes that have already been written.

        protected_fields = {
            "summary",
            "prelims_facts",
            "mains_analysis",
            "upsc_angle",
        }

        for field, value in article.items():

            if field in protected_fields and old.get(field):
                continue

            old[field] = value

        refreshed += 1

    archive = sorted(
        merged.values(),
        key=lambda item: item.get("date") or "",
        reverse=True,
    )

    return archive, added, refreshed


# ============================================================
# MAIN
# ============================================================

def main():

    print("=" * 55)
    print("UPSC MULTI-SOURCE NEWS COLLECTION")
    print("=" * 55)

    all_new_items = []
    source_success = 0

    for source in RSS_SOURCES:

        items = collect_feed(source)

        if items or source["name"] == "PIB":
            source_success += 1

        all_new_items.extend(items)

    # Do not destroy the existing archive if every feed fails.
    if not all_new_items:

        raise RuntimeError(
            "No articles were collected from any feed. "
            "Existing archive remains untouched."
        )

    existing = load_existing_archive()

    archive, added, refreshed = merge_archive(
        existing,
        all_new_items,
    )

    OUTPUT.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    OUTPUT.write_text(
        json.dumps(
            archive,
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    dated = sum(
        1 for item in archive if item.get("date")
    )

    undated = [
        item.get("title", "Untitled")
        for item in archive
        if not item.get("date")
    ]

    source_counts = {}

    for item in archive:

        name = item.get("source", "Unknown")

        source_counts[name] = (
            source_counts.get(name, 0) + 1
        )

    print()
    print("=" * 55)
    print("COLLECTION REPORT")
    print("=" * 55)

    print("Feed sources configured:", len(RSS_SOURCES))
    print("Articles received:", len(all_new_items))
    print("New articles added:", added)
    print("Existing articles refreshed:", refreshed)
    print("Total archive articles:", len(archive))
    print("Articles with dates:", dated)
    print("Articles without dates:", len(undated))

    print()
    print("ARTICLES BY SOURCE:")

    for name, count in sorted(source_counts.items()):
        print(name + ":", count)

    if undated:

        print()
        print("ARTICLES NEEDING DATE REVIEW:")

        for title in undated[:30]:
            print("-", title)

    print()
    print("IMPORTANT SOURCES STILL AWAITING CONNECTORS:")

    for source in SOURCE_DIRECTORY:
        print(
            "-",
            source["name"],
            "|",
            source["status"],
        )

    print()
    print("Archive saved successfully.")
    print("Existing notes and older articles were preserved.")


if __name__ == "__main__":
    main()
