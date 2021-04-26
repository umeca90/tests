# -*- coding: utf-8 -*-
import multiprocessing
import sys

from port_scanner import PortScanner
import argparse


def main():
    parser = argparse.ArgumentParser(prog='',
                                     description='Консольное приложение, принимающее на вход диапазон ip-адресов '
                                                 '(например 192.168.1.0/24)'
                                                 ' и список портов (например 80, 443, 22, 21, 25).'
                                                 ' Результатом - список открытых портов с указанием удаленного хоста.',
                                     usage='%(prog)s [options]')
    parser.add_argument('ip_range', type=str, help='диапазон ip-адресов(например 192.168.1.0/24)')

    parser.add_argument('ports', type=str, help="список портов (например 80, 443, 22, 21, 25).")

    parser.add_argument('--log_file', type=str, default='hosts.log', help="Файл для сохранения результата."
                                                                          "По умолчанию hosts.log")
    args = parser.parse_args()
    args_dict = vars(args)
    ports = list(map(int, args_dict['ports'].split(',')))
    args_dict.update({'ports': ports})
    multiprocessing.freeze_support()
    scanner = PortScanner(**args_dict)

    scanner.start()
    scanner.join()


if __name__ == '__main__':
    multiprocessing.freeze_support()
    main()
