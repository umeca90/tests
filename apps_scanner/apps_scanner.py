import json
import os
import time
import re
from multiprocessing import Process, Queue
from queue import Empty
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from bs4 import BeautifulSoup
import requests
from transliterate import translit

SCROLL_PAUSE_TIME = 0.7
DRIVER_PATH = '/Users/umeca90/code/tests/apps_scanner/chromedriver'
BASE_LINK = 'https://play.google.com'


class AppsScanner(Process):
    """
    Главный класс-процесс, отвечает за подготовку начальных ссылок, генерацию, запуск под-процессов
    и сохранение результата в формате json.
    """

    def __init__(self, app_name: str, json_file: str = 'data.json') -> None:
        super(AppsScanner, self).__init__()
        self.json_file = json_file
        self.app_name = app_name
        self.app_links = list()
        self.apps_info_queue = Queue()
        self.results = list()
        self.web_driver = None
        self.scanners = list()

    def run(self) -> None:
        self.init_web_driver()
        self.prepare_links()
        self._generate_scanners()
        for scanner in self.scanners:
            scanner.start()
        while True:
            try:
                app_info = self.apps_info_queue.get(timeout=0.001)
                self.results.append(app_info)
            except Empty:
                if not any(scanner.is_alive() for scanner in self.scanners):
                    break
        for scanner in self.scanners:
            scanner.join()
        self.web_driver.close()
        if self.results:
            self._save_info_to_json()
            path = os.path.join(os.path.dirname(os.path.abspath(__file__)), self.json_file)
            print(f'Скан окончен, результат сохранен в {path}')
        else:
            print('Скан не показал результатов')

    def init_web_driver(self) -> None:
        """
        Функция инициализирует вэб драйвер для анализа страниц.
        """
        opts = Options()
        opts.add_argument('-headless')
        self.web_driver = webdriver.Chrome(DRIVER_PATH, options=opts)

    def prepare_links(self) -> None:
        """"
        Функция делает запрос на главную ссылку через драйвер,
         запускает механизм обработки ссылок и производит фильтрацию ссылок.
        """
        self.web_driver.get(f'{BASE_LINK}/store/search?q={self.app_name}&c=apps')
        apps_tags = self.scroll_apps_on_page()
        for tag in apps_tags:
            link_tag = tag.find('div', {'class': ['b8cIId ReQCgd Q9MA7b']})
            app_name = link_tag.a.div.text
            if self.check_app_name(app_name):
                link = link_tag.a['href']
                if link not in self.app_links:
                    self.app_links.append(link)

    def scroll_apps_on_page(self) -> list:
        """
        Функция скролит страницу до тех пока, пока перестанут появляться необходимые теги,
        сохраняет теги в переменную и возвращает.
        """
        divs_len = 0
        while True:
            # Scroll down to bottom
            self.web_driver.execute_script("window.scrollTo(0, document.body.scrollHeight,);")
            # Wait to load page
            time.sleep(SCROLL_PAUSE_TIME)
            soup = BeautifulSoup(self.web_driver.page_source, features='html.parser')
            # Find all needed divs
            divs_soup = soup.find('div', {'class': ['ZmHEEd']})
            # Save found divs len
            new_divs_len = len(divs_soup.find_all('c-wiz', {'jsrenderer': ['PAQZbb']}))
            # Check len
            if new_divs_len == divs_len:
                break
            divs_len = new_divs_len
        base_app_tags = divs_soup.find_all('div', {'class': ['ImZGtf']})
        base_app_tags.extend(divs_soup.find_all('c-wiz', {'jsrenderer': ['PAQZbb']}))
        return base_app_tags

    def check_app_name(self, app_name: str) -> bool:
        """
        Функция проверяет изначальный тип ввода.
        Если данные содержат кириллицу, транслитит название приложения на ru.
        :param app_name: название приложения
        """
        cyrillic_input = re.search('[а-яА-Я]', self.app_name)
        if cyrillic_input:
            translited_app_name = translit(app_name, 'ru').lower()
            return translited_app_name[:4] in self.app_name
        else:
            return app_name[:5] in self.app_name

    def _generate_scanners(self) -> None:
        """
        Функция генерирует классы под-процессы для обработки тэгов с информацией.
        """
        self.scanners = [Scanner(link, self.apps_info_queue) for link in self.app_links]

    def _save_info_to_json(self):
        """
        Функция сохраняет результат в json файл.
        """
        with open('data.json', 'w', encoding='utf8') as file:
            file.write(json.dumps(self.results))


class Scanner(Process):
    """
    Класс под-процесс, отвечающий за создание запроса по полученной ссылке,
    обработку ответа и генерацию данных.
    """

    def __init__(self, link: str, queue: Queue) -> None:
        super(Scanner, self).__init__()
        self.link = link
        self.queue = queue
        self.soup = None
        self.app_info = dict()

    def run(self) -> None:
        self.prepare_soup()
        self.prepare_app_name()
        self.prepare_author_and_category()
        self.prepare_description()
        self.prepare_average_rate()
        self.prepare_rates_count()
        self.prepare_last_update()
        self.queue.put(self.app_info)

    def prepare_soup(self) -> None:
        """
        Функция делает http запрос, получает ответ и парсит верску для использования.
        """
        link = BASE_LINK + self.link
        self.app_info['link'] = link
        headers = {"Accept-Language": "ru - RU, ru;q=0.5"}
        response = requests.get(link, headers=headers)
        self.soup = BeautifulSoup(response.content, features='html.parser')

    def prepare_app_name(self) -> None:
        """
        Функция ищет в верстке тег, содержащий данные о названии приложени].
        """
        name_tag = self.soup.find('h1', {'class': ['AHFaub']})
        if name_tag:
            self.app_info['name'] = name_tag.span.text
        else:
            self.app_info['name'] = 'No name'

    def prepare_author_and_category(self) -> None:
        """
        Функция ищет в верстке теги, содержащие данные о авторстве и категории приложения.
        """
        author_and_category_tag = self.soup.find_all('span', {'class': ['T32cc']})
        if author_and_category_tag:
            author, category = author_and_category_tag
            self.app_info['author'], self.app_info['category'] = author.a.text, category.a.text
        else:
            self.app_info['author'] = self.app_info['category'] = 'No data'

    def prepare_description(self) -> None:
        """
        Функция ищет в верстке тег, содержащий описание приложения.
        """
        text = []
        description = self.soup.find('div', {'jsname': ["sngebd"]})
        if description:
            for child in description.children:
                string = child.string
                if string:
                    text.append(string)
            self.app_info['description'] = '\n'.join(text)
        else:
            self.app_info['description'] = 'No description'

    def prepare_average_rate(self) -> None:
        """
        Функция ищет в верстке тег, содержащий данные о средней оценке приложения.
        """
        av_rate = self.soup.find('div', {'class': ['BHMmbe']})
        if av_rate:
            self.app_info['average_rate'] = av_rate.text
        else:
            self.app_info['average_rate'] = 'No rates'

    def prepare_rates_count(self) -> None:
        """
        Функция ищет в верстке тег, содержащий данные о кол-ве оценок приложения.
        """
        div_tag = self.soup.find('span', {'class': ['AYi5wd']})
        if div_tag:
            rates_count = re.sub(r"(\xa0)", '', div_tag.span.text)
            self.app_info['rates_count'] = "{:,d}".format(int(rates_count))
        span_tag = self.soup.find('span', {'class': ['AYi5wd']})
        if span_tag:
            rates_count = re.sub(r"(\xa0)", '', div_tag.span.text)
            self.app_info['rates_count'] = "{:,d}".format(int(rates_count))
        else:
            self.app_info['rates_count'] = 'No rates'

    def prepare_last_update(self) -> None:
        """
        Функция ищет в верстке тег, содержащий данные о последнем обновлении.
        """
        last_update = self.soup.find('span', {'class': ['htlgb']})
        if last_update:
            self.app_info['last_update'] = last_update.text
        else:
            self.app_info['last_update'] = 'no data'
