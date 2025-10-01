import scrapy

class crawlPDF(scrapy.Spider):
    name = "crawlPDF"
    start_urls = [
        "https://arxiv.org/search/?query=machine+learning&searchtype=all&abstracts=show&size=25"
    ]

    custom_settings = {
        "FILES_STORE": "./downloaded_pdfs",
        "ITEM_PIPELINES": {"scrapy.pipelines.files.FilesPipeline": 1},
        "ROBOTSTXT_OBEY": False,
        "MEDIA_ALLOW_REDIRECTS": True,
    }

    count = 0
    max_pdfs = 10

    def parse(self, response):
        for paper in response.css("li.arxiv-result"):
            if self.count >= self.max_pdfs:
                return

            abs_link = paper.css("p.list-title a::attr(href)").get()
            if abs_link:
                paper_id = abs_link.split("/")[-1]
                pdf_url = f"https://arxiv.org/pdf/{paper_id}.pdf"
                self.count += 1
                yield {"file_urls": [pdf_url]}
