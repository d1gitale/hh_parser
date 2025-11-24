import pandas as pd


COLUMNS_HH = [
    "Ссылка на вакансию",
    "Название компании",
    "Телефон",
    "Сайт компании"
]

COLUMNS_RABOTA = [
    "Ссылка на вакансию",
    "Название компании",
    "Телефон",
    "Телефон компании",
    "Сайт компании"
]


def write_to_excel_hh(pages: list):
    data = {}
    for page in pages:
        data.update(page)

    data = [{**dict(zip(COLUMNS_HH, values))} for values in data.values()]

    df = pd.DataFrame(data)
    df.to_excel(
        'vacancies.xlsx',
        index=False
    )


def write_to_excel_rabota(pages: list):
    df = pd.DataFrame(pages)
    df.to_excel(
        'vacancies.xlsx',
        index=False,
        columns=COLUMNS_RABOTA
    )
