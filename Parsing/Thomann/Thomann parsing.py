import requests
import fake_useragent
from bs4 import BeautifulSoup
#Модель гитары | производитель | страна производства (если есть) | состояние (БУ/новая) | цена | рейтинг | сайт | ссылка | дата парсинга

link="https://www.thomannmusic.com/all-products-from-the-category-electric-guitars.html?filter=true&pg=3&ls=50&gk=GIEG&sp=solr_improved&cme=true"

user = fake_useragent.UserAgent().random

header = { 'user-agent':user}

responce=requests.get(link,headers=header)

soup=BeautifulSoup(responce,'lxml')