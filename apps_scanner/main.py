# -*- coding: utf-8 -*-
from apps_scanner import AppsScanner
import argparse


def main():
    parser = argparse.ArgumentParser(prog='',
                                     description='Консольное приложение для парсинга приложений в google play.',
                                     usage='%(prog)s [options]')
    parser.add_argument('app_name', type=str, help='название приложения для поиска(например сбербанк)')

    parser.add_argument('--json_file', type=str, default='data.json', help="Файл для сохранения результата."
                                                                           "По умолчанию data.json")
    args = parser.parse_args()
    args_dict = vars(args)
    scanner = AppsScanner(**args_dict)
    scanner.start()
    scanner.join()


if __name__ == '__main__':
    main()
