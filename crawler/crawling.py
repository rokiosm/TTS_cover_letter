import argparse
import concurrent.futures
import csv
import random
import re
import threading
import time
from pathlib import Path
from typing import Dict, Iterable, List, Optional
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup


BASE_URL = "https://linkareer.com"
SEARCH_URL = f"{BASE_URL}/cover-letter/search?page={{page}}"
DEFAULT_SORT = "RECENT_SCRAP_COUNT"
DEFAULT_TAB = "all"
THREAD_LOCAL = threading.local()

FIELDNAMES = ["기간", "회사", "직무", "유형", "스펙", "내용", "링크"]

PROMO_PATTERNS = [
    r"^이 글은 .+?자기소개서입니다\.?$",
    r".*어떻게 연결했는지 확인할 수 있습니다\.?$",
    r"^👉.*$",
    r".*링커리어 자소서 만능검색기.*$",
    r"^문장 스크랩$",
    r"^복사$",
    r"^공유$",
]

TAIL_PROMO_PATTERNS = [
    r"^🔥.*함께 확인.*$",
    r"^🔥.*추가 확인.*$",
    r"^🔥.*더보기.*$",
    r".*합격 자소서 함께 확인하세요!?$",
    r".*자소서 함께 확인하세요!?$",
    r".*자소서 함께 확인.*$",
    r".*합격 자소서 더보기.*$",
    r".*자기소개서 추가 확인.*$",
    r".*스크랩 TOP.*자소서.*$",
    r"^대학생 대외활동 공모전 채용 사이트 링커리어.*$",
    r"^https://linkareer\.com/?$",
    r"^https://linkareer\.com/cover-letter/\d+.*$",
    r"^https://abit\.ly/.*$",
]

QUESTION_START_PATTERNS = [
    r"^\[?\s*1(?:[-.]\d+)?\s*[\].)]",
    r"^1(?:[-.]\d+)?\s*[.)-]",
    r"^지원\s*동기",
    r"^지원동기",
    r"^본인에 대해",
    r"^자신을 가장 잘 표현",
]

LEADING_INTRO_PATTERNS = [
    r"^이 글은 .*",
    r".*참고해보세요\.?$",
    r".*살펴보세요\.?$",
    r".*드러난 글입니다\.?$",
    r".*강점입니다\.?$",
]


def build_session() -> requests.Session:
    session = requests.Session()
    session.headers.update(
        {
            "User-Agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/125.0 Safari/537.36"
            ),
            "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
        }
    )
    return session


def get_thread_session() -> requests.Session:
    session = getattr(THREAD_LOCAL, "session", None)
    if session is None:
        session = build_session()
        THREAD_LOCAL.session = session
    return session


def fetch(session: requests.Session, url: str, timeout: int = 20) -> str:
    response = session.get(url, timeout=timeout)
    response.raise_for_status()
    return response.text


def normalize_detail_url(href: str, page: Optional[int] = None) -> str:
    parsed = urlparse(urljoin(BASE_URL, href))
    match = re.search(r"/cover-letter/(\d+)", parsed.path)
    if not match:
        return ""

    detail_id = match.group(1)
    query_page = page if page is not None else 1
    return (
        f"{BASE_URL}/cover-letter/{detail_id}"
        f"?page={query_page}&sort={DEFAULT_SORT}&tab={DEFAULT_TAB}"
    )


def collect_links_from_search_page(session: requests.Session, page: int) -> List[str]:
    html = fetch(session, SEARCH_URL.format(page=page))
    soup = BeautifulSoup(html, "lxml")
    links: List[str] = []

    for anchor in soup.find_all("a", href=True):
        url = normalize_detail_url(anchor["href"], page=page)
        if url and url not in links:
            links.append(url)

    return links


def read_links_from_csv(input_csv: Path) -> Iterable[Dict[str, str]]:
    seen_links = set()
    with input_csv.open(newline="", encoding="utf-8-sig") as file:
        reader = csv.DictReader(file)
        for row in reader:
            link = row.get("링크", "")
            if not link:
                continue
            if link in seen_links:
                continue
            seen_links.add(link)
            yield {field: row.get(field, "") for field in FIELDNAMES}


def remove_noise_nodes(soup: BeautifulSoup) -> None:
    for selector in [
        "#selection-popover",
        "script",
        "style",
        "noscript",
        "button",
        "svg",
    ]:
        for node in soup.select(selector):
            node.decompose()


def clean_cover_letter_text(raw_text: str) -> str:
    lines = []
    for line in raw_text.splitlines():
        line = re.sub(r"\s+", " ", line).strip()
        if not line:
            continue
        if any(re.match(pattern, line) for pattern in TAIL_PROMO_PATTERNS):
            break
        if any(re.match(pattern, line) for pattern in PROMO_PATTERNS):
            continue
        lines.append(line)

    while lines and any(re.match(pattern, lines[0]) for pattern in LEADING_INTRO_PATTERNS):
        lines.pop(0)

    for index, line in enumerate(lines):
        if any(re.match(pattern, line) for pattern in QUESTION_START_PATTERNS):
            lines = lines[index:]
            break

    text = "\n\n".join(lines)

    # 상세 페이지 상단 소개문이 함께 잡히는 경우, 첫 번째 문항부터 남긴다.
    first_question = re.search(r"(?m)^\s*\[?\s*1(?:[-.]\d+)?\s*[\].)-]?\s+", text)
    if first_question:
        text = text[first_question.start() :].strip()

    # 불필요하게 반복되는 공백과 빈 줄을 정리한다.
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def extract_article_text(html: str) -> str:
    soup = BeautifulSoup(html, "lxml")
    remove_noise_nodes(soup)

    article = soup.select_one("#coverLetterContent article")
    if article is None:
        article = soup.select_one("#coverLetterContent")
    if article is None:
        article = soup.find("article")
    if article is None:
        return ""

    return clean_cover_letter_text(article.get_text("\n"))


def crawl_detail(session: requests.Session, row: Dict[str, str]) -> Dict[str, str]:
    html = fetch(session, row["링크"])
    content = extract_article_text(html)
    return {**row, "내용": content}


def write_rows(output_csv: Path, rows: Iterable[Dict[str, str]]) -> None:
    output_csv.parent.mkdir(parents=True, exist_ok=True)
    with output_csv.open("w", newline="", encoding="utf-8-sig") as file:
        writer = csv.DictWriter(file, fieldnames=FIELDNAMES)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in FIELDNAMES})


def sleep_between_requests(delay: float, jitter: float) -> None:
    wait = delay + random.uniform(0, jitter)
    if wait > 0:
        time.sleep(wait)


def crawl_from_existing_csv(args: argparse.Namespace) -> None:
    session = build_session()
    rows = list(read_links_from_csv(args.input_csv))
    if args.skip:
        rows = rows[args.skip :]
    if args.limit:
        rows = rows[: args.limit]
    total = len(rows)

    def crawl_row(item: tuple) -> Dict[str, str]:
        index, row = item
        try:
            row_session = get_thread_session() if args.workers > 1 else session
            crawled = crawl_detail(row_session, row)
            status = "ok" if crawled["내용"] else "empty"
            if index == 1 or index == total or index % args.progress_every == 0 or status == "empty":
                print(f"[{index}/{total}] {status}: {row['링크']}", flush=True)
            return crawled
        except Exception as exc:
            print(f"[{index}/{total}] failed: {row['링크']} ({exc})", flush=True)
            return row

    def generated_rows() -> Iterable[Dict[str, str]]:
        for index, row in enumerate(rows, start=1):
            yield crawl_row((index, row))
            sleep_between_requests(args.delay, args.jitter)

    def generated_parallel_rows() -> Iterable[Dict[str, str]]:
        indexed_rows = list(enumerate(rows, start=1))
        with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as executor:
            for crawled in executor.map(crawl_row, indexed_rows):
                yield crawled
                sleep_between_requests(args.delay, args.jitter)

    if args.append:
        rows_to_write = generated_parallel_rows() if args.workers > 1 else generated_rows()
        append_rows(args.output_csv, rows_to_write)
    else:
        rows_to_write = generated_parallel_rows() if args.workers > 1 else generated_rows()
        write_rows(args.output_csv, rows_to_write)


def read_existing_output_links(output_csv: Path) -> set:
    if not output_csv.exists():
        return set()

    with output_csv.open(newline="", encoding="utf-8-sig") as file:
        reader = csv.DictReader(file)
        return {row.get("링크", "") for row in reader if row.get("링크")}


def append_rows(output_csv: Path, rows: Iterable[Dict[str, str]]) -> None:
    output_csv.parent.mkdir(parents=True, exist_ok=True)
    existing_links = read_existing_output_links(output_csv)
    should_write_header = not output_csv.exists() or output_csv.stat().st_size == 0

    with output_csv.open("a", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=FIELDNAMES)
        if should_write_header:
            writer.writeheader()

        for row in rows:
            link = row.get("링크", "")
            if link in existing_links:
                continue
            writer.writerow({field: row.get(field, "") for field in FIELDNAMES})
            file.flush()
            existing_links.add(link)


def crawl_from_search_pages(args: argparse.Namespace) -> None:
    session = build_session()

    def generated_rows() -> Iterable[Dict[str, str]]:
        seen = set()
        for page in range(args.start_page, args.end_page + 1):
            if args.limit and len(seen) >= args.limit:
                break
            try:
                links = collect_links_from_search_page(session, page)
                print(f"[page {page}] found {len(links)} links")
            except Exception as exc:
                print(f"[page {page}] failed to collect links: {exc}")
                continue

            for link in links:
                if link in seen:
                    continue
                if args.limit and len(seen) >= args.limit:
                    break
                seen.add(link)
                row = {field: "" for field in FIELDNAMES}
                row["링크"] = link
                try:
                    crawled = crawl_detail(session, row)
                    status = "ok" if crawled["내용"] else "empty"
                    print(f"  - {status}: {link}")
                    yield crawled
                except Exception as exc:
                    print(f"  - failed: {link} ({exc})")
                    yield row
                sleep_between_requests(args.delay, args.jitter)

    write_rows(args.output_csv, generated_rows())


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="링커리어 합격 자기소개서 상세 본문을 CSV로 크롤링합니다."
    )
    parser.add_argument(
        "--input-csv",
        type=Path,
        help="기존 CSV의 링크를 다시 방문해서 내용 컬럼만 상세 본문으로 교체합니다.",
    )
    parser.add_argument(
        "--output-csv",
        type=Path,
        default=Path("linkareer_cover_letters_clean.csv"),
        help="저장할 CSV 경로입니다.",
    )
    parser.add_argument("--start-page", type=int, default=1)
    parser.add_argument("--end-page", type=int, default=740)
    parser.add_argument("--skip", type=int, default=0, help="기존 CSV에서 건너뛸 고유 링크 개수입니다.")
    parser.add_argument("--limit", type=int, help="저장할 최대 상세 페이지 개수입니다.")
    parser.add_argument("--append", action="store_true", help="output CSV에 중복 링크를 제외하고 이어서 씁니다.")
    parser.add_argument("--workers", type=int, default=1, help="상세 페이지를 병렬로 요청할 작업자 수입니다.")
    parser.add_argument("--progress-every", type=int, default=50, help="진행 로그를 출력할 간격입니다.")
    parser.add_argument("--delay", type=float, default=0.8)
    parser.add_argument("--jitter", type=float, default=0.4)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.input_csv:
        crawl_from_existing_csv(args)
    else:
        crawl_from_search_pages(args)


if __name__ == "__main__":
    main()
