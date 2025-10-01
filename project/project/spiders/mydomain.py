import scrapy


class MydomainSpider(scrapy.Spider):
    name = "mydomain"
    allowed_domains = ["mydomain.com"]
    start_urls = ["https://mydomain.com"]

    def parse(self, response):
        pass
