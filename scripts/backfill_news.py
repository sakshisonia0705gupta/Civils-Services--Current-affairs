
import json
import re
import time
from datetime import date, datetime, timezone
from pathlib import Path
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

START_DATE = date(2026, 4, 1)
END_DATE = date.today()

BASE_URL = "https://www.pib.gov.in/AllRelease.aspx"
PREVIEW = Path("data/backfill_preview.json")
REPORT = Path("data/backfill_report.json")

HEADERS = {
    "User-Agent": "Mozilla/5.0 UPSC-Intelligence-Hub/1.0"
}

TOPICS = {
    "Polity & Governance": r"constitution|supreme court|high court|judgment|judgement|parliament|bill|act\b|fundamental rights|federalism|election commission|governance|judiciary|data protection|tribunal",
    "Economy": r"rbi|reserve bank|repo rate|monetary policy|inflation|gdp|fiscal|budget|gst|tax|banking|financial inclusion|employment|poverty|exports|imports|trade|economic survey|sebi|cpi|iip",
    "International Relations": r"bilateral|diplomatic|foreign policy|united nations|wto|g20|brics|quad|indo.pacific|treaty|summit|international cooperation",
    "Environment": r"climate|biodiversity|wildlife|forest|wetland|ramsar|pollution|renewable energy|ecosystem|species|national park|conservation|sustainability",
    "Science & Technology": r"isro|space mission|satellite|artificial intelligence|quantum|semiconductor|biotechnology|genome|research|innovation|nuclear energy|digital technology",
    "Defence & Security": r"armed forces|military exercise|border security|cyber security|cybersecurity|internal security|coast guard|defence production|drdo",
    "Agriculture": r"agriculture|farmer|minimum support price|\bmsp\b|crop|irrigation|food security|fertilizer|fisheries|animal husbandry",
    "Society & Social Justice": r"public health|healthcare|nutrition|education|literacy|women empowerment|child welfare|social justice|tribal|sanitation|drinking water|disability",
    "History, Art & Culture": r"heritage|archaeology|unesco|museum|festival|traditional craft|handicraft|artisan|classical language|monument",
    "Reports & Institutions": r"report|index|ranking|census|survey|committee|commission|cag\b|statistics|parliamentary committee",
    "Disaster Management": r"disaster management|flood|drought|cyclone|earthquake|heatwave|early warning",
}

def classify(title):
    matches = []
    for topic, pattern in TOPICS.items():
        if re.search(pattern, title, re.I):
            matches.append(topic)
    return matches

def get_day_releases(day_value, month_value, year_value, session):
    response = session.get(BASE_URL, timeout=40)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")

    def hidden_value(name):
        element = soup.find("input", {"name": name})
        return element.get("value", "") if element else ""

    payload = {
        "__VIEWSTATE": hidden_value("__VIEWSTATE"),
        "__EVENTVALIDATION": hidden_value("__EVENTVALIDATION"),
        "__VIEWSTATEGENERATOR": hidden_value("__VIEWSTATEGENERATOR"),
        "__VIEWSTATEENCRYPTED": "",
        "__LASTFOCUS": "",
        "__EVENTTARGET": "ctl00$ContentPlaceHolder1$ddlMinistry",
        "__EVENTARGUMENT": "",
        "ctl00$Bar1$ddlregion": "3",
        "ctl00$Bar1$ddlLang": "1",
        "ctl00$ContentPlaceHolder1$ddlMinistry": "0",
        "ctl00$ContentPlaceHolder1$ddlday": str(day_value),
        "ctl00$ContentPlaceHolder1$ddlMonth": str(month_value),
        "ctl00$ContentPlaceHolder1$ddlYear": str(year_value),
    }

    response = session.post(
        BASE_URL,
        data=payload,
        headers={"Referer": BASE_URL},
        timeout=40
    )
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")
    area = soup.find("div", class_="content-area")

    if area is None:
        raise ValueError("PIB archive result area was not found")

    releases = []

    for item in area.find_all("li"):
        anchor = item.find("a", href=True)
        if not anchor:
            continue

        title = " ".join(anchor.get_text(" ", strip=True).split())
        link = urljoin(BASE_URL, anchor["href"])

        if not title or "pib.gov.in" not in link:
            continue

        link = link.replace("ReleseDetail", "ReleasePage")

        topics = classify(title)
        if not topics:
            continue

        releases.append({
            "title": title,
            "date": date(
                int(year_value), int(month_value), int(day_value)
            ).isoformat(),
            "month": f"{int(year_value):04d}-{int(month_value):02d}",
            "source": "PIB",
            "source_url": link,
            "upsc_subjects": topics,
            "priority": "Review",
            "review_status": "human_review_required",
            "notes_status": "not_prepared"
        })

    return releases

def month_range(start, end):
    current = date(start.year, start.month, 1)
    while current <= end:
        yield current.year, current.month
        if current.month == 12:
            current = date(current.year + 1, 1, 1)
        else:
            current = date(current.year, current.month + 1, 1)

def main():
    session = requests.Session()
    session.headers.update(HEADERS)

    all_records = []
    errors = []
    days_checked = 0

    for year, month in month_range(START_DATE, END_DATE):
        first = date(year, month, 1)
        if month == 12:
            next_month = date(year + 1, 1, 1)
        else:
            next_month = date(year, month + 1, 1)

        last_day = min(
            (next_month - date.resolution).day,
            (END_DATE - first).days + 1
        )

        print(f"Checking PIB: {year}-{month:02d}")

        for day in range(1, last_day + 1):
            try:
                records = get_day_releases(
                    day, month, year, session
                )
                all_records.extend(records)
                days_checked += 1
                print(
                    f"{year}-{month:02d}-{day:02d}: "
                    f"{len(records)} relevant candidates"
                )
                time.sleep(0.15)

            except Exception as error:
                errors.append({
                    "date": f"{year}-{month:02d}-{day:02d}",
                    "error": str(error)[:200]
                })
                print("FAILED:", year, month, day, str(error)[:120])

    unique = {}
    for item in all_records:
        unique[item["source_url"]] = item

    records = sorted(
        unique.values(),
        key=lambda x: (x["date"], x["title"].lower()),
        reverse=True
    )

    counts = {}
    for year, month in month_range(START_DATE, END_DATE):
        key = f"{year:04d}-{month:02d}"
        counts[key] = sum(
            1 for item in records if item["month"] == key
        )

    report = {
        "period_start": START_DATE.isoformat(),
        "period_end": END_DATE.isoformat(),
        "run_date_utc": datetime.now(timezone.utc).isoformat(),
        "source": "PIB All Releases archive",
        "days_checked": days_checked,
        "upsc_candidates": len(records),
        "monthly_candidate_counts": counts,
        "failed_dates": errors,
        "limitations": [
            "This is a title-based UPSC relevance screen.",
            "Candidates require review before becoming study material.",
            "Only headlines, dates and official links are collected.",
            "No full article text or AI-generated notes are claimed.",
            "The existing live news.json file is not modified."
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

    print("BACKFILL DIAGNOSTIC FINISHED")
    print("Candidates:", len(records))
    print("Days checked:", days_checked)
    print("Failed dates:", len(errors))
    print("Monthly counts:", counts)
    print("Live news.json was NOT changed.")

if __name__ == "__main__":
    main()
