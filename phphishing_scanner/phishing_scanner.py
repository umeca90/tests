import os
from multiprocessing import Process, Queue
import socket
from queue import Empty

from strategies import HomoglyphGeneratorStrategy, AdditionalSymbolStrategy, AddSubDomainStrategy, \
    RemoveSymbolStrategy

STRATEGIES = [HomoglyphGeneratorStrategy, AdditionalSymbolStrategy,
              AddSubDomainStrategy, RemoveSymbolStrategy]

DOMAIN_ZONES = ('com', 'ru', 'net', 'org', 'info', 'cn', 'es', 'top', 'au', 'pl', 'it', 'uk', 'tk', 'ml', 'ga', 'cf',
                'us', 'xyz', 'top', 'site', 'win', 'bid')


class PhishingScanner(Process):
    """
    Главный класс-процесс, отвечает за подготовку начальных данных, генерацию и запуск под-процессов.
    """

    def __init__(self, domain_string: str, ip_log_file: str = 'ip_log_file.log') -> None:
        super(PhishingScanner, self).__init__()
        self.domain_string = domain_string
        self.phishing_domains = list()
        self.domains_ip_queue = Queue()
        self.domains = list()
        self.scanners = list()
        self.results = dict()
        self._strategies = list()
        self.ip_log_file = ip_log_file

    @property
    def strategies(self) -> list:
        """
        Набор стратегий для обработки данных.
        """
        return self._strategies

    def run(self) -> None:
        self._prepare_strategies()
        for strategy in self.strategies:
            strategy.perform_strategy()
        self._prepare_domains()
        self._generate_scanners()
        for scanner in self.scanners:
            scanner.start()
        while True:
            try:
                ip_addr = self.domains_ip_queue.get(timeout=0.001)
                self.results.update(ip_addr)
            except Empty:
                if not any(scanner.is_alive() for scanner in self.scanners):
                    break
        for scanner in self.scanners:
            scanner.join()
        self._write_log_file()
        self._print_finishing_msg()

    def _prepare_strategies(self) -> None:
        """
        Функция запускает необходимые стратегии для генерации данных.
        """
        for strategy in STRATEGIES:
            self._strategies.append(strategy(self.domain_string, self.phishing_domains))

    def _prepare_domains(self) -> None:
        """
        Функция генерирует список доменов.
        """
        for domain_zone in DOMAIN_ZONES:
            for domain in self.phishing_domains:
                tmp_domain = domain + '.' + domain_zone
                self.domains.append(tmp_domain)

    def _generate_scanners(self) -> None:
        """
        Функция генерирует классы под-процессы для обработки доменов.
        """
        self.scanners = [Scanner(domain, self.domains_ip_queue) for domain in self.domains]

    def _write_log_file(self) -> None:
        """
        Функция записывает результат в файл.
        """
        with open(self.ip_log_file, 'w', encoding='utf8') as file:
            for domain, ip in self.results.items():
                str_msg = f'{domain} - {ip}'
                file.write(str_msg + '\n')

    def _print_finishing_msg(self) -> None:
        """
        Функция выводит результат на консоль.
        """
        if self.results:
            path = os.path.join(os.path.dirname(os.path.abspath(__file__)), self.ip_log_file)
            print(f'Скан окончен, результат сохранен в {path}, результат скана ниже')
            [print(f'{ip} - {domain}') for ip, domain in self.results.items()]
        else:
            print('Скан не показал результатов')


class Scanner(Process):
    """
    Класс под-процесс, подключение к переданному домену.
    """

    def __init__(self, domain, domains_ip_queue) -> None:
        super(Scanner, self).__init__()
        self.domain = domain
        self.domains_ip_queue = domains_ip_queue

    def run(self) -> None:
        self._process_request()

    def _process_request(self) -> None:
        """
        Функция создает подключение к домену, если оно успешно, передает в очередь название домена и ip адрес.
        """
        try:
            ip_address = socket.gethostbyname(self.domain)
            self.domains_ip_queue.put({self.domain: ip_address})
        except (ConnectionRefusedError, socket.error):
            pass

