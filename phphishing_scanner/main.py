# -*- coding: utf-8 -*-
from phishing_scanner import PhishingScanner
import argparse


def main():
    parser = argparse.ArgumentParser(prog='',
                                     description='Консольное приложение для поиска фишинговых ресурсов.',
                                     usage='%(prog)s [options]')
    parser.add_argument('domain_string', type=str, help='входное значение(например group-ib)')

    parser.add_argument('--ip_log_file', type=str, default='ip_log_file.log', help="Файл для сохранения результата."
                                                                             "По умолчанию ip_log_file.log")
    args = parser.parse_args()
    args_dict = vars(args)
    scanner = PhishingScanner(**args_dict)
    scanner.start()
    scanner.join()


if __name__ == '__main__':
    main()
