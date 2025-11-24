import aiohttp
import asyncio
from aiohttp.web_exceptions import HTTPException
from selenium.webdriver.chrome.options import Options
from selenium import webdriver
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager
from selenium.common.exceptions import (
    NoSuchElementException,
    ElementClickInterceptedException,
    ElementNotInteractableException
)
import bs4

from config import settings

class Parser():
    _vac_cards_selector = "div.r-serp__infinity-list > div.r-serp__item_vacancy"
    _vac_link_selector = "a.vacancy-preview-card__title_border"
    _vac_phone_button_selector = "a.vacancy-response__phones-show-link"
    _vac_phone_selector = "a.vacancy-response__phone > span"
    _company_name_selector = "div.vacancy-company-stats__name > a"
    _company_phone_button_selector = "span.info-table__text_cta"
    _company_phone_selector = "span.info-table__sub-item_block"
    _company_site_selector = "div.info-table__text > a"

    _timeout = aiohttp.ClientTimeout(2)


    def __init__(self) -> None:
        chrome_options = Options()
        chrome_options.add_argument("--headless=new")
        chrome_service = webdriver.ChromeService(ChromeDriverManager().install())
        self._driver = webdriver.Chrome(options=chrome_options)

    async def parse_page(self, vacancy_page_resp: aiohttp.ClientResponse, page: int) -> list:
        tasks = []
        soup = bs4.BeautifulSoup(await vacancy_page_resp.text(), 'html.parser')
        vacs = soup.select(self._vac_cards_selector)
        for vac in vacs:
            task = asyncio.create_task(self.parse_vac(vac))
            tasks.append(task)

        return await asyncio.gather(*tasks)

    async def parse_vac(self, vac_card: bs4.Tag) -> tuple[str, str, str, str, str]:
        wait_time = 1
        async with aiohttp.ClientSession() as session:
            for attempt in range(1, 4):
                try:
                    vac_a = vac_card.select_one(self._vac_link_selector)

                    if vac_a is not None:
                        vac_link = vac_a.attrs["href"] # don't think href will change
                    else:
                        raise ValueError(f"{self._vac_link_selector} is not found")

                    if vac_link is not None:
                        vac_link = settings.BASE_URL_RABOTA + str(vac_link) # pyright argues that _AttributeValue is not str
                    else:
                        raise ValueError(f"Attribute href not found on {self._vac_link_selector}")

                    async with session.get(vac_link, timeout=self._timeout) as resp:
                        if resp.status == 200:
                            soup = bs4.BeautifulSoup(await resp.text(), 'html.parser')

                            self._driver.get(vac_link)
                            try:
                                self._driver.find_element(By.CSS_SELECTOR, self._vac_phone_button_selector).click()
                                vacancy_phone = self._driver.find_element(By.CSS_SELECTOR, self._vac_phone_selector).text.strip()
                            except NoSuchElementException:
                                vacancy_phone = "Отсутствует"
                                print(f"{self._vac_phone_selector} selects zero elements in parse_vac")
                            except (ElementClickInterceptedException, ElementNotInteractableException):
                                vacancy_phone = "Отсутствует"
                                print(f"{self._vac_phone_button_selector} selects zero elements in parse_vac")

                            company_a = soup.select_one(self._company_name_selector)
                            if company_a is not None:
                                company_name = str(company_a.text.strip())
                                company_page_link = company_a.attrs["href"]
                                if company_page_link is not None:
                                    company_page_link = str(company_page_link)
                                else:
                                    raise ValueError(f"Attribute href not found on {self._company_name_selector}")
                            else:
                                raise ValueError(f"{self._company_name_selector} selects zero elements")

                            company_phone, company_site = await self.parse_company(company_page_link)

                            return vac_link, vacancy_phone, company_name, company_phone, company_site
                        else:
                            raise HTTPException(text=f"Failed to fetch vacancy page: {resp.status}")
                except HTTPException as e:
                    print(f"Request error in parse_vac on attempt {attempt}: {e}")
                    await asyncio.sleep(wait_time)
                    wait_time *= 1.5
                except aiohttp.ConnectionTimeoutError as e:
                    print(f"Connection timeout error in parse_vac on attempt {attempt}: {e}")
                    await asyncio.sleep(wait_time)
                except ValueError as e:
                    print(f"Element selecting error in parse_vac: {e}")
                    break
        return "", "", "", "", ""


    async def parse_company(self, company_link) -> tuple[str, str]:
        wait_time = 1
        async with aiohttp.ClientSession() as session:
            for attempt in range(1, 4):
                try:
                    async with session.get(company_link, timeout=self._timeout) as resp:
                        if resp.status == 200:
                            soup = bs4.BeautifulSoup(await resp.text(), 'html.parser')

                            self._driver.get(company_link)
                            try:
                                self._driver.find_element(By.CSS_SELECTOR, self._company_phone_button_selector).click()
                                company_phone = self._driver.find_element(By.CSS_SELECTOR, self._company_phone_selector).text.strip()
                            except NoSuchElementException:
                                company_phone = "Отсутствует"
                                print(f"{self._company_phone_selector} selects zero elements in parse_company")
                            except (ElementClickInterceptedException, ElementNotInteractableException):
                                company_phone = "Отсутствует"
                                print(f"{self._company_phone_button_selector} selects zero elements in parse_company")

                            company_site = soup.select_one(self._company_site_selector)
                            if company_site is not None:
                                company_site = str(company_site.text.strip())
                            else:
                                company_site = ""
                            return company_phone, company_site
                        else:
                            raise HTTPException(text=f"Failed to fetch company page: {resp.status}")
                except HTTPException as e:
                    print(f"HTTP error in parse_company on attempt {attempt}: {e}")
                    await asyncio.sleep(wait_time)
                    wait_time *= 1.5
                except aiohttp.ConnectionTimeoutError as e:
                    print(f"Connection timeout error in parse_company on attempt {attempt}: {e}")
                    await asyncio.sleep(wait_time)
                except ValueError as e:
                    print(f"Element selecting error in parse_company: {e}")
                    break
        return "", ""


    async def is_last_page(self, resp: aiohttp.ClientResponse):
        soup = bs4.BeautifulSoup(await resp.text(), 'html.parser')
        vac = soup.select_one("div.r-serp__infinity-list > div.r-serp__item_vacancy")
        if vac is None:
            print(resp.url)
            return True
        return False
