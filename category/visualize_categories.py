import csv
import html
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CATEGORY_DIR = ROOT / "categories"
OUTPUT_DIR = CATEGORY_DIR / "visualizations"


CHARTS = [
    ("직무_카테고리.csv", "직무_대분류", "job_large_category"),
    ("직무_카테고리.csv", "직무_중분류", "job_medium_category"),
    ("직무_카테고리.csv", "분류확신도", "job_confidence"),
    ("스펙_카테고리.csv", "기간", "spec_period"),
    ("스펙_카테고리.csv", "학교_분류", "spec_school_category"),
    ("스펙_카테고리.csv", "학과_계열", "spec_major_group"),
]


def read_rows(path):
    with path.open(newline="", encoding="utf-8-sig") as file:
        return list(csv.DictReader(file))


def write_summary_csv(path, counter):
    total = sum(counter.values())
    with path.open("w", newline="", encoding="utf-8-sig") as file:
        writer = csv.DictWriter(file, fieldnames=["항목", "건수", "비율"], lineterminator="\n")
        writer.writeheader()
        for label, count in counter.most_common():
            ratio = count / total if total else 0
            writer.writerow({"항목": label or "(빈값)", "건수": count, "비율": f"{ratio:.4f}"})


def write_bar_svg(path, title, counter, limit=25):
    items = counter.most_common(limit)
    width = 1100
    left = 260
    right = 80
    top = 70
    row_h = 30
    height = top + row_h * len(items) + 40
    max_count = max([count for _, count in items] or [1])
    total = sum(counter.values())
    chart_w = width - left - right

    lines = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="#ffffff"/>',
        f'<text x="24" y="36" font-family="Apple SD Gothic Neo, Arial, sans-serif" font-size="24" font-weight="700" fill="#222">{html.escape(title)}</text>',
        f'<text x="24" y="58" font-family="Apple SD Gothic Neo, Arial, sans-serif" font-size="13" fill="#666">총 {total:,}건, 상위 {len(items)}개 표시</text>',
    ]
    for index, (label, count) in enumerate(items):
        y = top + index * row_h
        bar_w = int(chart_w * count / max_count)
        pct = count / total * 100 if total else 0
        safe_label = html.escape(label or "(빈값)")
        lines.extend(
            [
                f'<text x="24" y="{y + 18}" font-family="Apple SD Gothic Neo, Arial, sans-serif" font-size="13" fill="#333">{safe_label}</text>',
                f'<rect x="{left}" y="{y + 4}" width="{bar_w}" height="18" rx="3" fill="#4f7cac"/>',
                f'<text x="{left + bar_w + 8}" y="{y + 18}" font-family="Arial, sans-serif" font-size="12" fill="#333">{count:,} ({pct:.1f}%)</text>',
            ]
        )
    lines.append("</svg>")
    path.write_text("\n".join(lines), encoding="utf-8")


def summarize_binary_presence(rows, column, output_name):
    counter = Counter("있음" if row.get(column, "").strip() else "없음" for row in rows)
    write_summary_csv(OUTPUT_DIR / f"{output_name}.csv", counter)
    write_bar_svg(OUTPUT_DIR / f"{output_name}.svg", f"{column} 유무", counter)


def write_index():
    svgs = sorted(OUTPUT_DIR.glob("*.svg"))
    sections = []
    for svg in svgs:
        title = svg.stem.replace("_", " ")
        sections.append(
            "\n".join(
                [
                    '<section class="chart">',
                    f"<h2>{html.escape(title)}</h2>",
                    f'<img src="{html.escape(svg.name)}" alt="{html.escape(title)}">',
                    "</section>",
                ]
            )
        )
    markup = f"""<!doctype html>
<html lang="ko">
<head>
  <meta charset="utf-8">
  <title>Category Visualizations</title>
  <style>
    body {{ margin: 24px; font-family: -apple-system, BlinkMacSystemFont, "Apple SD Gothic Neo", sans-serif; color: #222; }}
    h1 {{ font-size: 28px; margin-bottom: 8px; }}
    p {{ color: #666; }}
    .chart {{ margin: 28px 0 40px; }}
    .chart h2 {{ font-size: 18px; margin-bottom: 10px; }}
    img {{ max-width: 100%; border: 1px solid #ddd; }}
  </style>
</head>
<body>
  <h1>Category Visualizations</h1>
  <p>CSV 열별 분포를 SVG 막대차트로 정리했습니다.</p>
  {''.join(sections)}
</body>
</html>
"""
    (OUTPUT_DIR / "index.html").write_text(markup, encoding="utf-8")


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    cache = {}

    for filename, column, output_name in CHARTS:
        path = CATEGORY_DIR / filename
        rows = cache.setdefault(filename, read_rows(path))
        counter = Counter(row.get(column, "").strip() or "(빈값)" for row in rows)
        write_summary_csv(OUTPUT_DIR / f"{output_name}.csv", counter)
        write_bar_svg(OUTPUT_DIR / f"{output_name}.svg", column, counter)

    spec_rows = cache.setdefault("스펙_카테고리.csv", read_rows(CATEGORY_DIR / "스펙_카테고리.csv"))
    for column, output_name in [
        ("자격증", "spec_language_certificate_presence"),
        ("기타자격증", "spec_other_certificate_presence"),
        ("인턴", "spec_intern_presence"),
        ("기타", "spec_other_presence"),
    ]:
        summarize_binary_presence(spec_rows, column, output_name)

    write_index()
    print(f"visualization_dir={OUTPUT_DIR}")
    print(f"files={len(list(OUTPUT_DIR.glob('*')))}")


if __name__ == "__main__":
    main()
