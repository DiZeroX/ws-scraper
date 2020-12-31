# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: https://docs.scrapy.org/en/latest/topics/item-pipeline.html


# useful for handling different item types with a single interface
from itemadapter import ItemAdapter
import os

class WsScrapyPipeline:
    def process_item(self, item, spider):
        return item

class JktcgPipeline:
    def open_spider(self, spider):
        if not os.path.exists('output/jktcg/'):
            os.makedirs('output/jktcg')
        self.file = open('output/jktcg/scraped_sets.json', 'w')