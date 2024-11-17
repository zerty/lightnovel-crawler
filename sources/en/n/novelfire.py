# -*- coding: utf-8 -*-
import re
from typing import Generator
from lncrawl.templates.novelpub import NovelPubTemplate
from bs4 import BeautifulSoup, Tag
from lncrawl.models import Chapter

digit_regex = re.compile(r"page[-,=](\d+)")


class NovelFireCrawler(NovelPubTemplate):
    base_url = [
        "https://novelfire.net/",
    ]

    def initialize(self):
        self.init_executor(ratelimit=0.5)
        self.cleaner.bad_css.update(
            [
                ".adsbox",
                ".ad-container",
                "p > strong > strong",
                ".OUTBRAIN",
                "p[class]",
                ".ad",
                "p:nth-child(1) > strong",
                ".noveltopads",
                ".chadsticky",
                ".box-notification",
                "p > *",
            ]
        )

    def select_chapter_tags(self, soup: BeautifulSoup) -> Generator[Tag, None, None]:
        chapter_page = f"{self.novel_url.strip('/')}/chapters"
        soup = self.get_soup(chapter_page)
        page_count = max(
            [
                int(digit_regex.search(a["href"]).group(1))
                for a in soup.select(".pagination-container li a[href]")
            ]
        )
        if not page_count:
            page_count = 1

        futures = [self.executor.submit(lambda x: x, soup)]
        futures += [
            self.executor.submit(self.get_soup, f"{chapter_page}?page={p}")
            for p in range(2, page_count + 1)
        ]
        self.resolve_futures(futures, desc="TOC", unit="page")

        for f in futures:
            soup = f.result()
            yield from soup.select("ul.chapter-list li a")

    def select_chapter_body(self, soup: BeautifulSoup) -> Tag:
        self.browser.wait(".d-chapter-content")
        return soup.select_one(".d-chapter-content > #content")

    def visit_chapter_page_in_browser(self, chapter: Chapter) -> None:
        """Open the Chapter URL in the browser"""
        self.visit(chapter.url)
        self.browser.wait(".d-chapter-content", timeout=6)
