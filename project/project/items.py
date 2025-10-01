# Define here the models for your scraped items
#
# See documentation in:
# https://docs.scrapy.org/en/latest/topics/items.html

import scrapy


class ProjectItem(scrapy.Item):
    image_urls = scrapy.Field()   # danh sách link ảnh
    images = scrapy.Field()       # dữ liệu ảnh tải về
