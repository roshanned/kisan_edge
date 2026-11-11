"""Download the trusted-document RAG corpus -> corpus/raw/ and corpus/docs.jsonl (the manifest rag_ingest reads).

  python -m src.cloud.fetch_corpus            # Vikaspedia (Hindi + English) pages for the 4 crops and schemes, plus official PDFs
  python -m src.cloud.fetch_corpus --list     # only list what would be fetched
Vikaspedia (MeitY) renders each page's content into the page's __NEXT_DATA__ JSON, so it can be fetched by script.
Most other government sites time out from scripts; PDFs from them that fail are reported and can be added by hand.
Reruns skip files already in corpus/raw/.
"""
import argparse
import json
import re
import time
from collections import deque
from datetime import datetime, timezone
from pathlib import Path

import subprocess
from types import SimpleNamespace

import requests

RAW = Path("corpus/raw")
MANIFEST = Path("corpus/docs.jsonl")
UA = {"User-Agent": "Mozilla/5.0 (kisan-edge research corpus)"}
VP_HOST = {"hi": "https://agriculture.vikaspedia.in", "en": "https://en.vikaspedia.in"}
# Folders to crawl (Hindi slugs are Vikaspedia's own). Docs in crop folders are kept only if they match TOPIC.
# किसानों के लिए राज्य विशेष योजनाएं एवं सूचनाएं / उत्तर प्रदेश: UP-specific crop recommendations, all kept.
UP_FOLDER = ("/agriculture/91593f93893e92894b902-915947-93293f90f-93093e91c94d92f-93593f936947937-92f94b91c92893e90f902/"
             "90992494d924930-92a94d930926947936")
VP_ROOTS = {
    "hi": ["/agriculture/crop-production", "/agriculture/policies-and-schemes", "/agriculture/credit-and-insurance",
           "/agriculture/91594393793f-906917924",  # कृषि आगत (inputs)
           "/agriculture/91593f93893e92894b902-915947-93293f90f-93093e93794d91f94d93094092f-92f94b91c92893e90f902",  # राष्ट्रीय योजनाएं
           UP_FOLDER],
    "en": ["/agriculture/crop-production", "/agriculture/policies-and-schemes", "/agriculture/agri-insurance",
           "/agriculture/agri-inputs"],
}
CROP = re.compile(r"गेहू|गेहूँ|धान|चावल|सरसों|राई|तोरिया|गन्ना|wheat|rice|paddy|mustard|rapeseed|sugarcane", re.I)
TOPIC = re.compile(r"उर्वरक|खाद|कीटनाशक|कीट|रोग|खरपतवार|बीज|मृदा|मिट्टी|सिंचाई|fertili|pesticid|insect|pest|disease|weed|seed|soil|irrigat|"
                   r"योजना|बीमा|किसान|scheme|insurance|kisan|credit|pm-kisan|pmfby", re.I)
OFF_TOPIC = re.compile(r"पशु|मछली|मुर्गी|मधुमक्खी|रेशम|animal|fish|poultry|dairy|bee|sericult|livestock", re.I)
SCHEME_ROOTS = ("policies-and-schemes", "credit-and-insurance", "agri-insurance", "92f94b91c92893e90f902", UP_FOLDER)

# (doc_id, doc_key, url, source, date, lang, title). Dates are the document's own issue date.
PDFS = [
    ("pmkisan_og_2020", "pmkisan_guidelines", "https://pmkisan.gov.in/Documents/RevisedPM-KISANOperationalGuidelines(English).pdf",
     "PM-KISAN (MoA&FW)", "2020-03-29", "en", "PM-KISAN operational guidelines (revised)"),
    ("pmkisan_og_2019", "pmkisan_guidelines_2019", "https://pmkisan.gov.in/Documents/OPERATIONAL GUIDELINES.pdf",
     "PM-KISAN (MoA&FW)", "2019-02-24", "en", "PM-KISAN operational guidelines (original)"),
    # Not used: pmkisan.gov.in "प्रधानमंत्री किसान सम्मान निधि.pdf" is in a legacy (non-Unicode) Hindi font, so pypdf gives garbage.
    ("pmfby_og_revised", "pmfby_guidelines", "https://www.svnit.ac.in/Unnat_Bharat/PI/pdf/Agriculture & Organic Farming/Schemes by Government of India/"
     "PMFBY Pradhan Manti Fasal Bima Yojana/Annexure I Revised_Operational_Guidelines.pdf",
     "PMFBY (MoA&FW; SVNIT copy)", "2018-10-01", "en", "PMFBY operational guidelines (revised)"),
    ("pmfby_2020_changes", "pmfby_2020_changes", "https://static.pib.gov.in/WriteReadData/userfiles/688.pdf",
     "PIB", "2020-02-19", "en", "New provisions in the PMFBY operational guidelines (2020)"),
    ("cibrc_insecticides_2024", "cibrc_insecticides", "https://ppqs.gov.in/sites/default/files/major_uses_of_pesticides_insecticides_bio_insecticides_as_on_31.03.2024.pdf",
     "CIB&RC (PPQS)", "2024-03-31", "en", "Major uses of insecticides and bio-insecticides"),
    ("cibrc_biofungicides_2024", "cibrc_biofungicides", "https://ppqs.gov.in/sites/default/files/bio-fungicide_31.3.2024.pdf",
     "CIB&RC (PPQS)", "2024-03-31", "en", "Major uses of bio-fungicides"),
    ("cibrc_herbicides_2024", "cibrc_herbicides", "https://ppqs.gov.in/sites/default/files/major_uses_of_pesticides_herbicides_as_on_31.03.2024.pdf",
     "CIB&RC (PPQS)", "2024-03-31", "en", "Major uses of herbicides"),
    ("banned_pesticides_2021", "banned_pesticides", "https://hds.hp.gov.in/UploadedImages/RichTextDocument/list_of_pesticides_which_are_banned_20210310.pdf",
     "CIB&RC list (HP Govt copy)", "2021-03-10", "en", "Pesticides banned, refused registration and restricted in India"),
    ("gbpuat_varieties", "gbpuat_varieties", "https://www.gbpuat.ac.in/directorates/directorate_experiment/Released_crop_varieties.pdf",
     "GBPUAT Pantnagar", "2024-01-01", "en", "Crop varieties released by GBPUAT Pantnagar"),
    ("rbi_kcc_2018", "kcc_master_circular", "https://rbi.org.in/scripts/BS_ViewMasCirculardetails.aspx?id=11325",
     "RBI", "2018-07-04", "en", "Master circular: Kisan Credit Card scheme"),
]


def get(url, timeout=40):
    for attempt in range(3):
        try:
            r = requests.get(url, headers=UA, timeout=timeout)
            if r.status_code == 200:
                return r
        except requests.exceptions.SSLError:
            # Several .gov.in sites omit the intermediate certificate. curl on Windows verifies against the
            # OS store, which fetches the missing intermediate, so fall back to it (still verified).
            return curl(url, timeout)
        except requests.RequestException:
            pass
        time.sleep(2 * (attempt + 1))
    return None


def curl(url, timeout):
    p = subprocess.run(["curl", "-sfL", "--max-time", str(timeout), "-A", UA["User-Agent"], requests.utils.requote_uri(url)],
                       capture_output=True)
    return SimpleNamespace(content=p.stdout, text=p.stdout.decode("utf-8", "ignore")) if p.returncode == 0 else None


def vp_page(lang, path):
    r = get(f"{VP_HOST[lang]}/viewcontent{path}?lgn={lang}")
    if not r:
        return None
    m = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', r.text, re.S)
    return json.loads(m.group(1))["props"]["pageProps"] if m else None


def crawl_vikaspedia(lang, max_docs, roots=None):
    """BFS over folders; yields document records (path, title, date, html)."""
    seen, queue, found = set(), deque(roots or VP_ROOTS[lang]), []
    while queue and len(found) < max_docs:
        path = queue.popleft()
        if path in seen:
            continue
        seen.add(path)
        pp = vp_page(lang, path)
        time.sleep(0.3)
        if not pp:
            print(f"  skip (no page) {lang} {path}")
            continue
        in_scheme = any(s in path for s in SCHEME_ROOTS)
        in_crops = "crop-production" in path
        for item in pp.get("ssrContentList") or []:
            p, title = item["context_path"], item.get("title", "")
            if OFF_TOPIC.search(title + p):
                continue
            if item["context_type"] == "folder":
                queue.append(p)
            elif item["context_type"] == "document" and p not in seen and (
                    in_scheme or CROP.search(title + " " + p) or (not in_crops and TOPIC.search(title + " " + p))):
                seen.add(p)
                doc = vp_page(lang, p)
                time.sleep(0.3)
                c = (doc or {}).get("ssrPageContent") or {}
                if c.get("content"):
                    found.append({"path": p, "title": c.get("title", title).strip(), "html": c["content"],
                                  "date": iso_date(c.get("updated_at") or c.get("created_at"))})
                    print(f"  {lang} {len(found)} {c.get('title', title).strip()[:70]}")
    return found


# Scanned PDFs (no text layer), OCR'd by kaggle/jobs/05_ocr into corpus/raw/<doc_id>.txt.
# Tried and dropped: UP "Rabi_abhiyan_2022-23.pdf" is a campaign plan (area/seed targets), not crop advice, and OCR is noisy.
OCR_DOCS = {}

TNAU = "https://agritech.tnau.ac.in/crop_protection/"
TNAU_ROOTS = ["crop_prot_crop_insect_agri_pest.html", "crop_prot_crop_diseases_agri.html"]
TNAU_CROP = re.compile(r"paddy|rice|wheat|sugarcane|mustard|rapeseed|maize", re.I)


def crawl_tnau(max_pages):
    """TNAU Agritech crop-protection pages (pest/disease symptoms + management with doses) for our crops."""
    from urllib.parse import unquote, urljoin

    from bs4 import BeautifulSoup
    seen, queue, found = set(), deque(urljoin(TNAU, r) for r in TNAU_ROOTS), []
    while queue and len(found) < max_pages:
        url = queue.popleft()
        if url in seen:
            continue
        seen.add(url)
        r = get(url)
        time.sleep(0.3)
        if not r:
            continue
        soup = BeautifulSoup(r.content, "html.parser")
        for a in soup.find_all("a", href=True):
            nxt = urljoin(url, a["href"].split("#")[0]).replace("http://", "https://", 1)
            if nxt.startswith(TNAU) and "/ta/" not in nxt and TNAU_CROP.search(unquote(nxt)) and nxt not in seen:
                queue.append(nxt)
        if not TNAU_CROP.search(unquote(url)):
            continue
        for tag in soup(["script", "style", "nav", "header", "footer"]):
            tag.decompose()
        lines = soup.get_text("\n", strip=True).split("\n")
        # Drop the site menu (ends at the first "Contact") and footer (starts at the next "Home"); the first
        # content line is the breadcrumb, e.g. "Agricultural crops :: Cereals :: Rice Diseases".
        if "Contact" in lines:
            lines = lines[lines.index("Contact") + 1:]
        if "Home" in lines:
            lines = lines[:lines.index("Home")]
        text = "\n".join(lines)
        if len(text) > 400:
            crumb = lines[0].replace("Agricultural crops ::", "").strip() if lines else ""
            found.append({"url": url, "title": crumb or unquote(url.rsplit("/", 1)[-1]), "text": text})
            print(f"  tnau {len(found)} {unquote(url.rsplit('/', 1)[-1])[:70]}")
    return found


def iso_date(v):
    """Vikaspedia gives either an ISO string or epoch milliseconds."""
    if isinstance(v, (int, float)):
        return datetime.fromtimestamp(v / 1000, timezone.utc).date().isoformat()
    return (v or "")[:10]


def slug(path):
    return re.sub(r"\W+", "_", path.rsplit("/", 1)[-1].lower()).strip("_")[:60]


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--list", action="store_true")
    p.add_argument("--max-vp", type=int, default=150, help="max Vikaspedia docs per language")
    p.add_argument("--no-vp", action="store_true", help="skip the Vikaspedia crawl")
    p.add_argument("--vp-up-only", action="store_true", help="crawl only the Vikaspedia Uttar Pradesh folder")
    p.add_argument("--no-tnau", action="store_true", help="skip the TNAU crop-protection crawl")
    p.add_argument("--max-tnau", type=int, default=250)
    args = p.parse_args()
    RAW.mkdir(parents=True, exist_ok=True)
    records = {json.loads(l)["doc_id"]: json.loads(l) for l in MANIFEST.open(encoding="utf-8")} if MANIFEST.exists() else {}
    failed = []

    for doc_id, key, url, source, day, lang, title in PDFS:
        is_pdf = url.lower().endswith(".pdf")
        out = RAW / f"{doc_id}.{'pdf' if is_pdf else 'html'}"
        if args.list:
            print("doc", doc_id, url)
            continue
        if not out.exists():
            r = get(url, timeout=90)
            if not r or (is_pdf and not r.content.startswith(b"%PDF")):
                failed.append(f"{doc_id}  {url}")
                continue
            out.write_bytes(r.content)
            print(f"pdf {doc_id} {len(r.content) // 1024} KB")
        records[doc_id] = {"doc_id": doc_id, "doc_key": key, "path": f"raw/{out.name}", "source": source,
                           "date": day, "lang": lang, "title": title, "url": url}

    for lang in () if args.no_vp else ("hi",) if args.vp_up_only else ("hi", "en"):
        print(f"vikaspedia {lang}")
        for d in crawl_vikaspedia(lang, args.max_vp, [UP_FOLDER] if args.vp_up_only else None):
            doc_id = f"vp_{lang}_{slug(d['path'])}"
            if args.list:
                continue
            out = RAW / f"{doc_id}.html"
            out.write_text(f"<html><body><h1>{d['title']}</h1>\n{d['html']}</body></html>", encoding="utf-8")
            records[doc_id] = {"doc_id": doc_id, "doc_key": doc_id, "path": f"raw/{out.name}", "source": "Vikaspedia (MeitY)",
                               "date": d["date"] or "2020-01-01", "lang": lang, "title": d["title"],
                               "url": f"{VP_HOST[lang]}/viewcontent{d['path']}?lgn={lang}"}

    for doc_id, (url, source, day, title) in OCR_DOCS.items():
        if (RAW / f"{doc_id}.txt").exists():
            records[doc_id] = {"doc_id": doc_id, "doc_key": doc_id, "path": f"raw/{doc_id}.txt", "source": source,
                               "date": day, "lang": "hi", "title": title, "url": url}
        else:
            print(f"OCR text missing for {doc_id}: run kaggle/jobs/05_ocr and copy the .txt into corpus/raw/")

    if not args.no_tnau and not args.list:
        print("tnau")
        for d in crawl_tnau(args.max_tnau):
            doc_id = f"tnau_{slug(d['url'].replace('.html', ''))}"
            out = RAW / f"{doc_id}.txt"
            out.write_text(f"{d['title']}\n\n{d['text']}", encoding="utf-8")
            records[doc_id] = {"doc_id": doc_id, "doc_key": doc_id, "path": f"raw/{out.name}", "source": "TNAU Agritech Portal",
                               "date": "2020-01-01", "lang": "en", "title": d["title"], "url": d["url"]}

    if not args.list:
        with MANIFEST.open("w", encoding="utf-8") as f:
            for r in sorted(records.values(), key=lambda r: r["doc_id"]):
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
        print(f"{len(records)} docs -> {MANIFEST}")
    if failed:
        print("FAILED (download by hand into corpus/raw/ with this doc_id):\n  " + "\n  ".join(failed))


if __name__ == "__main__":
    main()
