"""
Download MathonGo JEE Main chapter-wise PYQ PDFs for any year/session/subject.

Usage examples:
    python mathongo_pyq.py maths january-2026
    python mathongo_pyq.py physics april-2025
    python mathongo_pyq.py chemistry feb-2021
    python mathongo_pyq.py all all            # every subject, every session
    python mathongo_pyq.py --list             # show available sessions

Requires: pip install requests beautifulsoup4 gdown
"""
import os, re, sys, time, zipfile
import requests, gdown
from bs4 import BeautifulSoup

BASE = "https://www.mathongo.com/iit-jee/"
INDEX = BASE + "jee-main-chapter-wise-questions-with-solutions"
UA = {"User-Agent": "Mozilla/5.0"}
SHORTENERS = ("cutt.ly", "links.mathongo.com", "bit.ly", "drive.google.com", "tinyurl.com")
GENERIC = {"download", "click here", "download pdf", "pdf", "here", "link"}

# Session slugs as used on the site (they're not consistent: "jan" vs "january").
SESSIONS = [
    "january-2026",
    "january-2025", "april-2025",
    "january-2024", "april-2024",
    "january-2023", "april-2023",
    "june-2022", "july-2022",
    "feb-2021", "mar-2021", "july-2021", "august-2021",
    "jan-2020", "sep-2020",
    "jan-2019", "april-2019",
]
SUBJECTS = ["maths", "physics", "chemistry"]


def page_url(subject, session):
    return f"{BASE}jee-main-{subject}-chapter-wise-questions-with-solutions-{session}"


def find_links(html):
    """Return [(chapter_name, short_url)] from a subject page."""
    soup = BeautifulSoup(html, "html.parser")
    out, seen = [], set()
    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        if not any(s in href for s in SHORTENERS) or href in seen:
            continue
        name = a.get_text(" ", strip=True)
        # If the link text is a serial number or just "Download", take the
        # longest non-numeric cell in the same table row as the chapter name
        if not name or name.isdigit() or name.lower() in GENERIC:
            row = a.find_parent("tr")
            if row:
                cells = [td.get_text(" ", strip=True) for td in row.find_all(["td", "th"])]
                cells = [c for c in cells if c and not c.isdigit() and c.lower() not in GENERIC]
                if cells:
                    name = max(cells, key=len)
        seen.add(href)
        out.append((name or f"file_{len(out)+1}", href))
    return out


DRIVE_RE = re.compile(r'https://(?:drive|docs)\.google\.com/[^"\'\s<>]+')


def resolve(url, tries=5):
    """Follow a short link to its Google Drive URL. Retries when cutt.ly rate-limits."""
    if "google.com" in url:
        return url
    for attempt in range(tries):
        try:
            r = requests.get(url, headers=UA, allow_redirects=True, timeout=30)
            # walk the redirect chain looking for a Drive URL
            for h in list(r.history) + [r]:
                loc = h.headers.get("Location", "")
                if "google.com" in loc:
                    return loc
            if "google.com" in r.url:
                return r.url
            m = DRIVE_RE.search(r.text)          # JS / meta-refresh redirect
            if m:
                return m.group(0)
        except requests.RequestException:
            pass
        wait = 5 * (attempt + 1)
        print(f"     ...no redirect yet, retrying in {wait}s")
        time.sleep(wait)
    return url


def drive_id(url):
    m = re.search(r"/d/([\w-]{20,})|[?&]id=([\w-]{20,})", url)
    return (m.group(1) or m.group(2)) if m else None


def safe(name):
    return re.sub(r'[\\/:*?"<>|]+', "_", name)[:120]


def download_page(subject, session, root="pyq"):
    url = page_url(subject, session)
    r = requests.get(url, headers=UA, timeout=30)
    if r.status_code != 200:
        print(f"!! {url} -> HTTP {r.status_code}")
        return None
    links = find_links(r.text)
    if not links:
        print(f"!! no download links found on {url}")
        return None

    folder = os.path.join(root, f"JEE_Main_{session}_{subject}")
    os.makedirs(folder, exist_ok=True)
    print(f"\n== {subject} {session}: {len(links)} links ==")

    for i, (name, short) in enumerate(links, 1):
        drive = resolve(short)
        out = os.path.join(folder, f"{i:02d} {safe(name)}.pdf")
        if os.path.exists(out) and os.path.getsize(out) > 0:
            print("have", name); continue
        try:
            if "/folders/" in drive:            # a whole Drive folder
                gdown.download_folder(url=drive, output=folder, quiet=True)
            elif drive_id(drive):
                res = gdown.download(f"https://drive.google.com/uc?id={drive_id(drive)}",
                                     out, quiet=True)
                if not res or not os.path.exists(out):
                    print("FAIL", name, "- Drive refused (file private or quota hit)"); continue
            else:
                print("SKIP", name, "->", drive); continue
            print("OK  ", name)
            time.sleep(1.5)   # be gentle with cutt.ly / Drive
        except Exception as e:
            print("FAIL", name, "-", e)

    zip_path = folder + ".zip"
    with zipfile.ZipFile(zip_path, "w") as z:
        for f in sorted(os.listdir(folder)):
            z.write(os.path.join(folder, f), f)
    print("Zipped ->", zip_path)
    return zip_path


if __name__ == "__main__":
    if "--list" in sys.argv:
        print("Subjects:", ", ".join(SUBJECTS))
        print("Sessions:", ", ".join(SESSIONS))
        sys.exit()
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    subj, sess = sys.argv[1].lower(), sys.argv[2].lower()
    subjects = SUBJECTS if subj == "all" else [subj]
    sessions = SESSIONS if sess == "all" else [sess]
    for s in subjects:
        for ss in sessions:
            download_page(s, ss)