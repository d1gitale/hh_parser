import argparse


parser = argparse.ArgumentParser(description='Поиск вакансий на HH/rabota.ru')
parser.add_argument('query', type=str, help='Поисковой запрос')
parser.add_argument('--rabota', action='store_true', help='Парсинг с rabota.ru')
args = parser.parse_args()
