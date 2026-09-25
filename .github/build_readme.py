#!/usr/bin/env python3
"""Generate a polished README.md for a customer doc repo from its folder contents.

Usage (from the repo root):
    python3 .github/build_readme.py . "Customer Name"

New top-level folders must be added to THEMES first, otherwise the script exits
and lists the folders that aren't mapped yet.
"""
import re
import subprocess
import sys
from datetime import date
from pathlib import Path
from urllib.parse import quote

THEMES = [
    ("🧠", "AI & GenAI", "Agents, gateways, and generative AI strategy", [
        ("🚪", "AI Gateway & Omnigent", "Unity AI Gateway product decks and overviews"),
        ("✨", "GenAI", "Generative AI big books and enterprise AI guides"),
        ("🧩", "Omnigent", "Omnigent meta-harness for AI agents"),
        ("🤖", "AI Agents", "Agent research and industry reports"),
    ]),
    ("🧞", "Genie", "Plan, build, deploy, and secure AI/BI Genie", [
        ("🧞", "Genie (Best Practices)", "AI/BI Genie best practices, curation, and pitch material"),
        ("🚀", "Genie (Deploy Guides)", "Genie rollout, migration, and enterprise deployment"),
        ("🔐", "Genie (Security Reviews)", "Genie security reviews, threat model, and controls for InfoSec assessments"),
        ("🔒", "Genie (Security & Governance)", "AI/Genie security, guardrails, and governance frameworks"),
    ]),
    ("🗂️", "Governance & Data", "Unity Catalog, semantic layers, and data modelling", [
        ("📐", "Semantic-Modelling", "UC Metric Views and semantic layer modeling"),
        ("📚", "Unity Catalogue", "Unity Catalog design, best practices, and governance"),
        ("🧱", "Data Modelling", "Dimensional and Data Vault modeling for the Lakehouse"),
        ("🛡️", "Data Governance & Lineage", "Data & AI governance and lineage guidance"),
    ]),
    ("⚙️", "Platform & Ops", "Deployment, cost management, apps, and cloud architecture", [
        ("📦", "DABS", "Databricks Asset Bundles — CI/CD and declarative deployment"),
        ("💰", "FinOps", "Cost control, budgeting, tagging, and observability"),
        ("🖥️", "Databricks Apps", "Building and deploying data & AI apps on Databricks"),
        ("☁️", "Azure", "Azure Databricks architecture and capability comparisons"),
        ("⚡", "Lakehouse :: RT", "Lakehouse real-time processing"),
    ]),
    ("📣", "Announcements", "The latest from Data + AI Summit", [
        ("📣", "DAIS 2026 Announcements", "Data + AI Summit 2026 announcements"),
    ]),
]

# Curated "Start here" cards: (icon, title, blurb, [(folder, filename), ...])
FEATURED = [
    ("🔐", "Security Review Pack", "Everything an InfoSec team needs to assess Genie.", [
        ("Genie (Security Reviews)", "How does Databricks secure Genie.pdf"),
        ("Genie (Security Reviews)", "Databricks Genie Security Threat Model.pdf"),
        ("Genie (Security Reviews)", "Controls for Genie.xlsx"),
    ]),
    ("🚀", "Roll Out Genie", "From space design to an enterprise-wide rollout.", [
        ("Genie (Deploy Guides)", "[External] Genie Enterprise Deployment Guide .pdf"),
        ("Genie (Deploy Guides)", "Genie_Space-Design-Guide.pdf"),
        ("Genie (Deploy Guides)", "[EXTERNAL] Genie Space Rollout Plan Template.pdf"),
    ]),
    ("📚", "Govern & Optimise", "Build a well-governed, cost-efficient lakehouse.", [
        ("Unity Catalogue", "Unity Catalog - Best Practices and Rapid Start.pdf"),
        ("Semantic-Modelling", "Building Semantic Models in Databricks with UC Metric Views.pdf"),
        ("FinOps", "[EXTERNAL] Cost Mgmt & Tagging Best Practices.pdf"),
    ]),
]

ICONS = {"PDF": "📄", "DOCX": "📝", "XLSX": "📊", "XLSM": "📊", "JPG": "🖼️", "PNG": "🖼️", "PPTX": "📽️"}
TOP = "#-databricks-document-repository"


def enc(path: str) -> str:
    return "/".join(quote(p, safe="").replace("(", "%28").replace(")", "%29") for p in path.split("/"))


def slug(heading: str) -> str:
    s = "".join(c for c in heading.lower() if c.isalnum() or c in " -_")
    return "#" + s.replace(" ", "-")


def display(name: str) -> str:
    return re.sub(r"\s{2,}", " ", Path(name).stem).strip()


def ext(name: str) -> str:
    return Path(name).suffix.lstrip(".").upper()


def main(repo: Path, customer: str) -> None:
    tracked = subprocess.run(["git", "-C", str(repo), "ls-files", "-z"], capture_output=True, text=True, check=True).stdout
    docs: dict[str, list[str]] = {}
    for line in tracked.split("\0"):
        if "/" in line and not line.startswith("."):
            folder, name = line.split("/", 1)
            if "/" not in name:
                docs.setdefault(folder, []).append(name)
    for v in docs.values():
        v.sort(key=lambda n: display(n).casefold())

    configured = {t for _, _, _, topics in THEMES for _, t, _ in topics}
    missing = sorted(set(docs) - configured)
    if missing:
        sys.exit(f"Folders not mapped to a theme: {missing}")

    total = sum(len(docs.get(t, [])) for t in configured)
    n_topics = sum(1 for t in configured if docs.get(t))
    fmts = sorted({ext(n) for v in docs.values() for n in v})
    fmt_badge = quote(" | ".join(fmts), safe="")
    today = date.today().strftime("%B %Y")
    out: list[str] = []
    w = out.append

    # ---- Hero ----
    w(f"""<div align="center">

<img src=".github/banner.svg" alt="Databricks Document Repository — {customer}" width="100%">

# 📖 Databricks Document Repository

### {customer} · Curated Databricks Knowledge Library

*Product decks, best-practice guides, deployment playbooks, and security reviews,<br>
curated by your Databricks account team and organised so you can find what you need fast.*

<br>

![Documents](https://img.shields.io/badge/Documents-{total}-FF3621?style=for-the-badge&logo=databricks&logoColor=white)
![Topics](https://img.shields.io/badge/Topics-{n_topics}-1B3139?style=for-the-badge)
![Formats](https://img.shields.io/badge/Formats-{fmt_badge}-00A972?style=for-the-badge)
![Updated](https://img.shields.io/badge/Updated-{quote(today)}-6B7280?style=for-the-badge)

<br>

<b>{" &nbsp;·&nbsp; ".join(f'<a href="{slug(f"{i} {t}")}">{i} {t}</a>' for i, t, _, _ in THEMES)}</b>

</div>

<br>
""")

    # ---- Start here ----
    w("## ⭐ Start Here\n")
    w("Three curated reading paths, each one a good place to begin.\n")
    w('<table>\n<tr>')
    for icon, title, blurb, items in FEATURED:
        links = "<br>".join(
            f'▸ <a href="{enc(f"{folder}/{name}")}">{display(name)}</a>'
            for folder, name in items if name in docs.get(folder, [])
        )
        w(f'<td width="33%" valign="top">\n\n### {icon} {title}\n<sub>{blurb}</sub>\n\n{links}\n\n</td>')
    w('</tr>\n</table>\n')

    # ---- At a glance ----
    w("## 🗺️ The Library at a Glance\n")
    w("| Theme | Topic | Docs | What you'll find |\n|:--|:--|:--:|:--|")
    for ticon, theme, _, topics in THEMES:
        first = True
        for icon, topic, desc in topics:
            if not docs.get(topic):
                continue
            label = f"**{ticon} {theme}**" if first else ""
            w(f"| {label} | {icon} [{topic}]({slug(f'{icon} {topic}')}) | `{len(docs[topic])}` | {desc} |")
            first = False
    w(f"\n<p align=\"right\"><sub><b>{total}</b> documents · <b>{n_topics}</b> topics · <b>{len(THEMES)}</b> themes</sub></p>\n")

    # ---- How to use ----
    w("""## 🧭 How to Use This Library

| | |
|:--|:--|
| 🔎 **Browse** | Start with a theme above, or press <kbd>Ctrl</kbd>/<kbd>⌘</kbd> + <kbd>F</kbd> to search by keyword. |
| 👁️ **Preview** | Click any title. PDFs and images render in the browser; Office files download. |
| ⬇️ **Download** | Open a document and select the download button (top right). |
| 📦 **Get everything** | Use **Code → Download ZIP** to take the whole library offline. |
| 🏷️ **Sharing** | Files tagged `[External]` or `[Customer Facing]` are cleared for wider distribution. Everything else is shared with your organisation by your Databricks account team, so please check with us before passing it on to anyone outside it. |

---
""")

    # ---- Sections ----
    for ticon, theme, tdesc, topics in THEMES:
        present = [t for t in topics if docs.get(t[1])]
        if not present:
            continue
        w(f"# {ticon} {theme}\n")
        w(f"<sub>{tdesc}</sub>\n")
        for icon, topic, desc in present:
            files = docs[topic]
            w(f"## {icon} {topic}\n")
            w(f"> {desc} &nbsp;·&nbsp; **{len(files)}** {'document' if len(files) == 1 else 'documents'} &nbsp;·&nbsp; [📂 Open folder]({enc(topic)})\n")
            w("| | Document | Format |\n|:--:|:--|:--:|")
            for name in files:
                e = ext(name)
                w(f"| {ICONS.get(e, '📎')} | [{display(name)}]({enc(f'{topic}/{name}')}) | `{e}` |")
            w(f"\n<p align=\"right\"><sub><a href=\"{TOP}\">↑ Back to top</a></sub></p>\n")
        w("---\n")

    # ---- Footer ----
    w(f"""<div align="center">

<br>

**Need something that isn't here?** Reach out to your Databricks account team and we'll add it.

<sub>{customer} · Databricks Document Repository · Last updated {today}</sub>

</div>
""")
    (repo / "README.md").write_text("\n".join(out))
    print(f"{repo.name}: {total} docs, {n_topics} topics")


if __name__ == "__main__":
    main(Path(sys.argv[1]), sys.argv[2])
