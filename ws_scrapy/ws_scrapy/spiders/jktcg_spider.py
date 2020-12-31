import scrapy
import json
import os
import requests
import shutil

class JktcgSpider(scrapy.Spider):
    name = "jktcg"

    start_urls = [
        'http://jktcg.com/MenuLeftEN.html'
    ]

    if not os.path.exists("output/jktcg/"):
        os.makedirs("output/jktcg")

    scraped_sets_path = 'output/jktcg/scraped_sets.txt'
    scraped_sets_file = open(scraped_sets_path, "a+", encoding="utf-8")

    def parse(self, response):
        self.scraped_sets_file.seek(0)
        scraped_lines = self.scraped_sets_file.readlines()
        scraped_sets = set()
        if scraped_lines:
            for line in scraped_lines:
                scraped_sets.add(line.rstrip('\n'))

        cardset_links = response.css('.content a::attr(href)').getall()

        cardset_links = set(cardset_links)

        cardset_links = cardset_links - scraped_sets

        for href in cardset_links:
            yield response.follow(href, callback=self.parse_iframe, meta={'href': href})
        # yield from response.follow_all(test_list, callback=self.parse_iframe)

    def parse_iframe(self, response):
        # set_id = response.url[17:-1]
        iframe_source = response.css('iframe::attr(src)').getall()[1]
        cardset_link = response.urljoin(iframe_source)
        yield response.follow(cardset_link, callback=self.parse_cardset, meta={'href': response.meta.get('href')})

    def parse_cardset(self, response):
        set_id = response.meta.get('href')
        set_name = response.css('ins::text').get().strip()
        set_data = {
            'id': set_id,
            'name': set_name,
            'cards': {}
        }

        images_folder_path = f'output/jktcg/images/{set_id}'
        if not os.path.exists(images_folder_path):
            os.makedirs(images_folder_path)

        for card in response.css('td'):
            if not card.css('td>a'):
                continue

            raw_text = card.css('td::text').getall()

            collection_id = raw_text[0].strip().replace('/', '-')
            name_en = raw_text[4].strip()
            img_url = card.css('a::attr(href)').get().replace('\t', '')
            img_url = response.urljoin(img_url)

            # download card image
            card_img_path = f'output/jktcg/images/{set_id}/{collection_id}.jpg'
            if not os.path.exists(card_img_path):
                card_img = requests.get(img_url, stream=True)
                if card_img.status_code == 200:
                    card_img.raw.decode_content = True
                    with open(card_img_path, "wb") as f:
                        shutil.copyfileobj(card_img.raw, f)
                    self.logger.debug(f'Downloaded card image {collection_id} for set {set_id}')
                else:
                    self.logger.error(f'Unable to download card image {collection_id} for set {set_id}')

            card_data = {
                'collection_id': collection_id,
                'name_en': name_en,
                'img_url': img_url
            }

            set_data['cards'][collection_id] = card_data
            # yield {
            #     'collection_id': raw_text[0].strip(),
            #     'name_en': raw_text[4].strip(),
            #     'img_url': img_url
            # }
        if not os.path.exists('output/jktcg/data/'):
            os.makedirs('output/jktcg/data')
        with open(f"output/jktcg/data/{set_id}.json", "w") as write_file:
            json.dump(set_data, write_file)

        self.scraped_sets_file.write(f'{set_id}\n')
        self.scraped_sets_file.flush()

    def closed(self, reason):
        self.scraped_sets_file.close()

