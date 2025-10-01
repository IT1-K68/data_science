import scrapy
from project.items import ProjectItem

class ExampleSpider(scrapy.Spider):
    name = "example"
    start_urls = ["https://example.com"]

    def parse(self, response):
        item = ProjectItem()
        item['image_urls'] = response.css("img::attr(src)").getall()
        yield item
