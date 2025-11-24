import aiohttp

from cli import args
from config import settings
import hh
import rabota
import utils


async def main():
    if args.rabota:
        rabota_parser = rabota.Parser()
        tasks = []
        page = 1

        async with aiohttp.ClientSession() as session:
            while True:
                for attempt in range(1, 4):
                    try:
                        async with session.get(
                            settings.BASE_URL_RABOTA + f"/vacancy/?query={args.query}&is_employers_only=true&page={page}",
                            timeout=aiohttp.ClientTimeout(2)
                        ) as resp:
                            if await rabota_parser.is_last_page(resp):
                                break

                            if resp.status != 200:
                                print(f"Request for page {page} on attempt {attempt} failed with status code {resp.status}")
                                continue
                            else:
                                task = asyncio.create_task(rabota_parser.parse_page(resp, page))
                                tasks.append(task)
                    except (aiohttp.ConnectionTimeoutError, asyncio.TimeoutError) as e:
                        print(f"Connection timeout error in parse_vac on attempt {attempt}: {e}")
                        await asyncio.sleep(1)
                page += 1

        utils.write_to_excel_rabota(await asyncio.gather(*tasks))

    else:
        hh_parser = hh.Parser()
        tasks = []

        async with aiohttp.ClientSession() as session:
            async with session.get(
                settings.BASE_URL_HH + f'/vacancies?area=2&label=not_from_agency&search_fields=name&text={args.query}'
            ) as found_check:
                found = (await found_check.json(encoding="utf-8"))["found"]
                pages = (found + settings.PER_PAGE_HH - 1) // settings.PER_PAGE_HH
            for page in range(pages):
                task = asyncio.create_task(hh_parser.fetch_page(page))
                tasks.append(task)

        utils.write_to_excel_hh(await asyncio.gather(*tasks))


if __name__ == '__main__':
    import asyncio
    asyncio.run(main())


# area - 2 (СПБ)
# label - not_from_agency (не от агенств)
# search_fields - name (в названии вакансии)
# text - arbitrary

# resp["items"] - все вакансии
# item["alternate_url"] - ссылка на вакансию
# item["emloyer"]["name"] - название компании
# item["contacts"]["phones"] - список телефонов на вакансии
# item["employer"]["id"] - id работодателя

# employer - работодатель, получен через /employers/{employer_id}
# employer["site_url"] - сайт работодателя
