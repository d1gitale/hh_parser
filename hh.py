import asyncio
import aiohttp

from config import settings
from cli import args

from collections import namedtuple


Site = namedtuple("Site", ["url", "vac_id"])


class Parser():

    _company_cache: dict[str, str] = {}
    _company_cache_lock = asyncio.Lock()
    _req_semaphore = asyncio.Semaphore(8)


    async def fetch_company_cached(self, employer_id: str, vac_id: str) -> Site:
        if employer_id in self._company_cache:
            return Site(self._company_cache[employer_id], vac_id)

        async with self._company_cache_lock:
            if employer_id in self._company_cache:
                return Site(self._company_cache[employer_id], vac_id)

            try:
                company_site = await self._fetch_company_site(employer_id)
                self._company_cache[employer_id] = company_site
                return Site(company_site, vac_id)
            except Exception as e:
                print(f"⚠️ Не удалось загрузить компанию {employer_id}: {e}")
                return Site("Нет сайта", vac_id)

    async def _fetch_company_site(self, employer_id: str) -> str:
        async with aiohttp.ClientSession() as session:
            for attempt in range(3):
                try:
                    async with session.get(
                        f"{settings.BASE_URL_HH}/employers/{employer_id}"
                    ) as resp:
                        if resp.status != 200:
                            raise Exception(f"HTTP {resp.status}: {await resp.text()}")
                        return (await resp.json())["site_url"]
                except Exception as e:
                    if attempt < 2:
                        print(f"⚠️ Не удалось загрузить страницу работодателя: {e}")
                        wait_time = 2 ** attempt
                        await asyncio.sleep(wait_time)
                    else:
                        return "Нет сайта"


    async def fetch_page(self, page: int) -> dict:
        async with self._req_semaphore:
            async with aiohttp.ClientSession() as session:
                for attempt in range(3):
                    try:
                        async with session.get(
                            settings.BASE_URL_HH + f'/vacancies?area=2&label=not_from_agency&search_fields=name&text={args.query}&per_page={settings.PER_PAGE_HH}&page={page}'
                        ) as resp:
                            if resp.status != 200:
                                raise Exception(f"HTTP {resp.status}: {await resp.text()}")
                            vacancies = (await resp.json(encoding="utf-8"))["items"]
                            break

                    except Exception as e:
                        if attempt < 2:
                            print(f"⚠️ Не удалось загрузить страницу {page}: {e}")
                            wait_time = 2 ** attempt
                            await asyncio.sleep(wait_time)
                        else:
                            return {}

        vac_data = {}
        tasks = []
        for vac in vacancies:
            try:
                task = asyncio.create_task(self.fetch_company_cached(vac["employer"]["id"], vac["id"]))
                tasks.append(task)
                vac_data[vac["id"]] = [
                    vac["alternate_url"],
                    vac["employer"]["name"],
                    self.construct_phone(vac["contacts"]["phones"]) if vac["contacts"] is not None else "Отсутствует"
                ]
            except KeyError:
                print(f"⚠️ Не удалось получить id работодателя: {vac['employer']}")

        sites = await asyncio.gather(*tasks)
        for site in sites:
            vac_data[site.vac_id].append(site.url)

        return vac_data


    def construct_phone(self, phones: list[dict]):
        phone_strs = []
        for phone in phones:
            phone_strs.append(phone["country"] + phone["city"] + phone["number"])
        return ", ".join(phone_strs)
