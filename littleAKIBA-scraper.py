import os
from pathlib import Path
from datetime import datetime
import requests
import shutil
import json
from bs4 import BeautifulSoup

class CardSetBasic:
    def __init__(self, t="", l="", i=""):
        self.title = t
        self.link = l
        self.img = i    

BASE_URL = "https://littleakiba.com/tcg/weiss-schwarz/"
if not os.path.exists("output/littleakiba/"):
    os.makedirs("output/littleakiba")

log = open("output/littleakiba/log.txt", "a", encoding="utf-8")
log.write(f"\n{datetime.now()}\n")
scraped_sets_file = open("output/littleakiba/scraped_sets.txt", "a+", encoding="utf-8")
scraped_sets = []
scraped_sets_file.seek(0)
scraped_lines = scraped_sets_file.readlines()
if scraped_lines:
    for line in scraped_lines:
        split_line = line.split("<-=->")
        line_title = split_line[0]
        line_link = split_line[1].rstrip("\n")
        scraped_sets.append(CardSetBasic(line_title, line_link))

# retrieve all set links and titles
sets_page = requests.get(BASE_URL)
if (sets_page.status_code != 200):
    log.write(f"ERROR: Unable to download {BASE_URL}\n")
    exit

sets_soup = BeautifulSoup(sets_page.content, 'lxml')

sets_list_element = sets_soup.find("ul") # first ul tag is list of all sets

sets_list = []
for sets_item_element in sets_list_element.contents:
    if (sets_item_element.name != "li"):
        continue
    try:
        if (sets_item_element["class"][0] == "disabled"):
            continue
    except KeyError:
        pass
    title = sets_item_element.find("p").string
    link = sets_item_element.find("a")["href"]
    image = sets_item_element.find("a").find("img")["data-src"]
    card_set = CardSetBasic(title, link, image)
    sets_list.append(card_set)

# filter out sets that have already been scraped
filtered_sets = []
for set_item in sets_list:
    set_exists = False
    for scraped_set in scraped_sets:
        if (set_item.title == scraped_set.title and set_item.link == scraped_set.link):
            set_exists = True
            break
    if (not set_exists): 
        log.write(f"New set {set_item.title} - {set_item.link}\n")
        filtered_sets.append(set_item)
if (not filtered_sets):
    log.write("EXIT: No new sets\n")
    exit

# Iterate through new sets to scrape
for new_set in filtered_sets:
    new_set_page = requests.get(BASE_URL + new_set.link)
    if (new_set_page.status_code != 200):
        log.write(f"ERROR: Unable to download {BASE_URL}{new_set.link}\n")
        continue
    
    new_set_soup = BeautifulSoup(new_set_page.content, "lxml")
    new_set_header_element = new_set_soup.find("input", attrs={"name":"series_id", "type":"hidden"})
    new_set_id = new_set_header_element.find_next_sibling().text[5:-1].replace("/", "-")
    
    new_path = f"output/littleakiba/images/{new_set_id}"
    Path(new_path).mkdir(parents=True, exist_ok=True) # TODO: remove exist_ok and log warning

    # download cover image for set
    cover_path = f"output/littleakiba/images/{new_set_id}/cover.jpg"
    if (not Path(cover_path).exists()):
        cover_img = requests.get(new_set.img, stream=True)
        if (cover_img.status_code == 200):
            cover_img.raw.decode_content = True
            with open(cover_path, "wb") as f:
                shutil.copyfileobj(cover_img.raw, f)
            log.write(f"Downloaded cover image for set {new_set_id}\n")
        else:
            log.write(f"ERROR: Unable to download cover image for set {new_set_id}\n")

    # create list of links to cards within set
    card_links = []
    card_list_element = new_set_soup.find("div", class_="card_list")
    for element in card_list_element.find_all("a"):
        card_links.append(element["href"])

    # create object for the set
    set_object = {
        "id": new_set_id,
        "name": new_set.title,
        "cards": {}
    }

    # Iterate through each link and scrape card info
    for card_link in card_links:
        card_page = requests.get(card_link)
        if (card_page.status_code != 200):
            log.write(f"ERROR: Unable to download {card_link}\n")
            continue

        card_soup = BeautifulSoup(card_page.content, "lxml")
        card_details_element = card_soup.find("div", class_="card_details")

        card_rarity = ""
        card_id = card_details_element.find("small").text.replace("/", "-")
        card_id_split = card_id.split()

        if (len(card_id_split) == 1): # incomplete id, probably missing rarity
            log.write(f"Incomplete card_id: {card_id}\n")
            print(f"Incomplete card_id: {card_id}")
            card_collection_id = card_id_split[0].rstrip(" ")
            card_rarity = "ERROR"
        else:
            card_collection_id = card_id_split[0]
            card_rarity = card_id.split()[1]
        card_id = card_id.replace(" ", "_")

        # download card image
        card_image_link = card_details_element.find("div", class_="image").find("a", class_="fullview")["href"]
        card_path = f"output/littleakiba/images/{new_set_id}/{card_id}.jpg" #TODO: implement card id
        if (not Path(card_path).exists()):
            card_img = requests.get(card_image_link, stream=True)
            if (card_img.status_code == 200):
                card_img.raw.decode_content = True
                with open(card_path, "wb") as f:
                    shutil.copyfileobj(card_img.raw, f)
                log.write(f"Downloaded card image {card_id} for set {new_set_id}\n")
            else:
                log.write(f"ERROR: Unable to download card image {card_id} for set {new_set_id}\n")

        card_name_jp = ""
        card_name_en = ""
        card_name_element = card_details_element.find("h4")
        if (len(card_name_element.contents) == 5): #some sets have card names are translated
            log.write("Card name is translated")
            card_name_jp = card_name_element.contents[0].rstrip()
            card_name_en = card_name_element.contents[2].rstrip("\t")
        else:
            card_name_jp = card_details_element.find("h4").text
        
        card_stat_list_element = card_details_element.find("ul")
        card_stat_list_item_elements = card_stat_list_element.find_all("li")
        
        card_type = card_stat_list_item_elements[0].contents[2].lstrip(" ")
        card_color = card_stat_list_item_elements[1].contents[2].lstrip(" ")
        card_level = card_stat_list_item_elements[2].contents[2].lstrip(" ")
        card_cost = card_stat_list_item_elements[3].contents[2].lstrip(" ")
        card_trigger = card_stat_list_item_elements[4].contents[2].lstrip(" ")
        card_power = card_stat_list_item_elements[5].contents[2].lstrip(" ")
        card_soul = ""
        card_trait_en_1 = ""
        card_trait_en_2 = ""
        card_trait_jp_1 = ""
        card_trait_jp_2 = ""
        if (card_type == "Character" and card_name_jp != "先攻後攻カード"):
            card_soul = card_stat_list_item_elements[6].contents[2].lstrip(" ")
            card_traits_element =  card_stat_list_item_elements[7].contents[1].contents[2]
            if (len(card_traits_element.contents) > 1):
                card_trait_en_1 = card_traits_element.contents[0].lstrip()[:-2]
                card_trait_jp_1 = card_traits_element.contents[1].text
                if (len(card_traits_element.contents) == 7): # 2 traits
                    card_trait_en_2 = card_traits_element.contents[4][:-2]
                    card_trait_jp_2 = card_traits_element.contents[5].text
        
        # card text
        card_text_element = card_details_element.find("p", text="Card Text/Abilities:")
        
        card_text_en_element = card_text_element.next_sibling.next_sibling
        card_text_en = card_text_en_element.text
        card_text_jp_element = card_text_en_element.next_sibling.next_sibling
        card_text_jp = card_text_jp_element.text
        card_flavor_jp_element = card_details_element.find("p", text="Flavor Text:").next_sibling.next_sibling.next_sibling.next_sibling
        card_flavor_jp = card_flavor_jp_element.text
        if (card_flavor_jp == "-"):
            card_flavor_jp = ""

        card_data = {
            "name_jp": card_name_jp,
            "name_en": card_name_en,
            "collection_id": card_collection_id,
            "rarity": card_rarity,
            "type": card_type,
            "color": card_color,
            "level": card_level,
            "cost": card_cost,
            "trigger": card_trigger,
            "power": card_power,
            "soul": card_soul,
            "trait_en_1": card_trait_en_1,
            "trait_en_2": card_trait_en_2,
            "trait_jp_1": card_trait_jp_1,
            "trait_jp_2": card_trait_jp_2,
            "effect_en": card_text_en,
            "effect_jp": card_text_jp,
            "flavor_jp": card_flavor_jp
        }

        set_object["cards"][card_id] = card_data

    new_path = "output/littleakiba/data/"
    Path(new_path).mkdir(parents=True, exist_ok=True) # TODO: remove exist_ok and log warning

    with open(f"output/littleakiba/data/{new_set_id}.json", "w") as write_file:
        json.dump(set_object, write_file, indent=2)
    
    scraped_sets_file.write(f"{new_set.title}<-=->{new_set.link}\n")
    scraped_sets_file.flush()
    log.flush()
    print(f"Completed set: {new_set.title}")

scraped_sets_file.close()
log.close()
 


