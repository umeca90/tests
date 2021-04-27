# -*- coding: utf-8 -*-

import ipaddress
import os
import socket
import sys
from collections import namedtuple
from multiprocessing import Process, Queue
from queue import Empty
from typing import Union

host_fields = ('ip', 'port', 'status', 'server')
Host = namedtuple('Host', host_fields, defaults=(None,) * len(host_fields))

WEB_PORTS = [80, 443]


class PortScanner(Process):
    """
    Класс процесс, отвечает за подготовку начальных данных, порождение подпроцессов, сохранение и вывод результата.
    :param ip_range - диапазон ip адресов в виде строки 192.168.1.0/24
    :param ports - список портов для сканирования.
    :param log_file - файл для сохранения результата.
    """

    def __init__(self, ip_range: str, ports: list, log_file='hosts.log', *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.ports = ports
        self.ip_range = ip_range
        self.ip_list = list()
        self.scanners = list()
        self.hosts_queue = Queue(maxsize=10)
        self.opened_hosts = list()
        self.hosts_file = log_file

    def run(self) -> None:
        """
        Главная функция класса, готовит начальные данные,
        порождает процессы, завершает процессы, сохраняет результат
        выводит на консоль сообщение с результатом.
        """
        self._prepare_ip_v4_objects()
        self._generate_scanners()
        for scanner in self.scanners:
            scanner.start()
        while True:
            try:
                host = self.hosts_queue.get(timeout=0.001)
                self.opened_hosts.append(host)
            except Empty:
                if not any(scanner.is_alive() for scanner in self.scanners):
                    break
        for scanner in self.scanners:
            scanner.join()

        if self.opened_hosts:
            path = os.path.join(os.path.dirname(os.path.abspath(__file__)), self.hosts_file)
            print('Скан закончен, результат ниже:')
            print(f'Результат сохранен в {path}')
            self._print_hosts_msg()
            self._write_log_file()
        else:
            print('Открытые хосты не обнаружены.')

    def _prepare_ip_v4_objects(self) -> None:
        """
        Функция создает список ip адресов и присваивает его переменной self.ip_list.
        """
        try:
            self.ip_list = list(ipaddress.ip_network(self.ip_range))
        except ValueError as err:
            sys.exit(err)

    def _generate_scanners(self) -> None:
        """
        Функция порождает процесс на каждый объект в переменной self.ip_list.
        """
        self.scanners = [Scanner(ip_v4, self.ports, self.hosts_queue) for ip_v4 in self.ip_list]

    def _write_log_file(self) -> None:
        """
        Функция записывает результат в файл.
        """
        with open(self.hosts_file, 'w', encoding='utf8') as file:
            for host in self.opened_hosts:
                str_msg = self._generate_msg_string(host)
                file.write(str_msg + '\n')

    def _print_hosts_msg(self) -> None:
        """
        Функция выводит результат на консоль.
        """
        msg_strings = list()
        for host in self.opened_hosts:
            str_msg = self._generate_msg_string(host)
            msg_strings.append(str_msg)
        [print(msg) for msg in msg_strings]

    def _generate_msg_string(self, host) -> str:
        """
        Функция подготавливает и возвращает текстовую строку для вывода на консоль и записи в файл.
        """
        tms_list = list()
        host_dict = host._asdict()
        for value in host_dict.values():
            if value:
                tms_list.append(str(value))
        str_msg = ' '.join(tms_list)
        return str_msg


class Scanner(Process):
    """
    Класс под-процесс, порожденный классом PortScanner.
     Получает на вход объект IPv4Address, порты и 'очередь' для передачи результата выполнения.
     Создает подключения по переданному адресу и портам, проверяет, удачно ли подключение,
     генерирует информацию о подключении и передает в главный процесс PortScanner.
    """

    def __init__(self, ip_v4: ipaddress.IPv4Address, ports: list, hosts_queue: Queue, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.ip_v4 = ip_v4
        self.ports = ports
        self.hosts_queue = hosts_queue
        self.timeout = 0.3

    def run(self) -> None:
        self.check_ports()

    def check_ports(self) -> None:
        """
        Функция запускает итерирует по всем портам и, в зависимости от порта, запускает функцию сканирования.
        """
        for port in self.ports:
            if port in WEB_PORTS:
                self.scan_port_with_header(port)
            else:
                self.scan_port(port)

    def scan_port_with_header(self, port) -> None:
        """
        Функция сканирует хост по 80 и 443 порту.
         Передает успешный результат сканирования в очередь главного процесса.
        """
        try:
            request_string = f"GET / HTTP/1.1\nHost: {str(self.ip_v4)}\n\n"
            bytes_request_string = str.encode(request_string)
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sct:
                sct.settimeout(self.timeout)
                sct.connect((str(self.ip_v4), port))
                sct.sendall(bytes_request_string)
                response_data = sct.recv(1024)

            try:
                decoded_string = response_data.decode("UTF-8")
            except UnicodeDecodeError:
                decoded_string = response_data.decode("cp1252")

            response_data_list = decoded_string.split('\r\n')
            http_server = self._check_server_info(response_data_list)
            host = Host(ip=str(self.ip_v4), port=port, status='OPEN', server=http_server)
            self.hosts_queue.put(host)
        except (ConnectionRefusedError, socket.error):
            pass

    def scan_port(self, port) -> None:
        """
        Функция сканирует хост по остальным портам.
         Передает успешный результат сканирования в очередь главного процесса.
        """
        sct = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sct.settimeout(self.timeout)
        connected = sct.connect_ex((str(self.ip_v4), port)) == 1
        if connected:
            tmp_host = Host(ip=str(self.ip_v4), port=port, status='OPEN', server=None)
            self.hosts_queue.put(tmp_host)

    def _check_server_info(self, response_data: list) -> Union[str, None]:
        """
        Функция проверяет header полученный от сервера.
        :param response_data: header - содержит заголовки.
        :return http_server: строка с ПО сервера.
        """
        for header_data in response_data:
            if 'server' in header_data.lower():
                http_server = header_data.split(':')[-1]
                return http_server

        return None
