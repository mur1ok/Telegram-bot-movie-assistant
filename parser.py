import aiohttp
import asyncio
from bs4 import BeautifulSoup
from aiogram.utils.markdown import hide_link, hlink
import json
from yandexfreetranslate import YandexFreeTranslate
from databse import DataBaseHandler


class RequestParser:
    def __init__(self):
        headers = {
            'User-agent':
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
                '(KHTML, like Gecko) Chrome/107.0.0.0 Safari/537.36'
        }
        self._session = aiohttp.ClientSession(headers=headers)

    def _prepare_text(self, raw_text: str) -> str:
        """
        Turns a raw request from the user into text for Google queries.
        If the genre is not specified in the query, then by default it adds the word "фильм" to the query
        :param raw_text: raw request from user
        """
        raw_text = raw_text.lower()
        move_types = ["фильм", "сериал", "аниме", "анимэ", "мульт"]
        for move_type in move_types:
            if move_type in raw_text:
                return "+".join(raw_text.split())
        raw_text = raw_text + " фильм"
        return "+".join(raw_text.split())

    async def _take_online_cinema_from_google(self, raw_text: str) -> dict[str, str]:
        """
        Makes a request to Google and searches for links to online movie theaters where you can watch this movie
        :return: Dictionary, where the key is the abbreviated name of the site,
                 and the value is the full path to the site.
        """
        raw_text = self._prepare_text(raw_text)
        async with self._session.get(f"https://www.google.com/search?q={raw_text}") as response:
            soup = BeautifulSoup(await response.text(), "html.parser")
            permitted_links: list[str] = [
                "kinopoisk.ru",
                "ivi.ru",
                "okko",
                "more.tv",
                "kion",
                "wink.ru",
                "lordfilm",
                "animego",
                "film.ru",
                "amediateka",
                "Okko",
                "shikimori",
                "ani.best",
                "jut-su",
                "ururuanime",
                "lordserials"
            ]
            links: dict[str, str] = dict()
            for link in soup.find_all("a", href=True):
                for permitted_link in permitted_links:
                    if permitted_link in link.get('href'):
                        permitted_links.remove(permitted_link)
                        links[permitted_link.capitalize()] = link.get('href')
            return links

    async def _take_info(self, raw_text: str) -> tuple[str, str, float, str] | tuple[None, None, None, None]:
        """
        By the name of the film, he makes a request to Google, where he tries to find a link to IMDB
        with this film in order to extract the title, description, rating and poster from it.
        If there is no such movie, then None is returned instead of all the expected values.
        """
        raw_text = self._prepare_text(raw_text)
        async with self._session.get(f"https://www.google.com/search?q={raw_text}+imdb.com") as imdb_search:
            soup = BeautifulSoup(await imdb_search.text(), "html.parser")
            for link in soup.find_all("a", href=True):
                if "https://www.imdb.com" in link.get('href'):
                    imdb_link = link.get('href')
                    break
        try:
            async with self._session.get(imdb_link) as imdb_cite:
                soup = BeautifulSoup(await imdb_cite.text(), "html.parser")

                name: str = soup.find("meta", {"name": "description"}).get("content").split(":")[0]

                info_dict = json.loads(soup.find_all("script", {"type": "application/ld+json"})[0].text)
                description: str = YandexFreeTranslate().translate("en", "ru",
                                                                   info_dict["description"].replace("&apos;", "'"))

                link_to_poster: str = info_dict["image"]
                rating = float(info_dict["aggregateRating"]['ratingValue'])
                return name, description, rating, link_to_poster
        except Exception:
            return None, None, None, None

    async def take_formatted_message(self, row_user_request: str, username: str, db: DataBaseHandler) -> str:
        name_description_rating_poster, links = await asyncio.gather(self._take_info(row_user_request),
                                                                     self._take_online_cinema_from_google(
                                                                         row_user_request))

        film_name: str | None = name_description_rating_poster[0]
        description: str | None = name_description_rating_poster[1]
        rating: float | None = name_description_rating_poster[2]
        poster_link: str | None = name_description_rating_poster[3]
        result = ""
        if poster_link is not None:
            result += f'{hide_link(poster_link)}'
        if film_name is not None:
            result += f"<b>{film_name}</b>\n\n"
        else:
            return "<b>Я не смог найти фильма с таким названием</b> 😔\n"
        if description is not None:
            result += f"{description}\n"
        else:
            result += "<b>Описание я найти не смог</b>\n"
        if rating is not None:
            if rating <= 3:
                result += f"\n<b>Оценка:</b> {rating} / 10 😔\n"
            elif 3 < rating <= 6.8:
                result += f"\n<b>Оценка:</b> {rating} / 10 🙂\n"
            else:
                result += f"\n<b>Оценка:</b> {rating} / 10 🤩\n"

        if len(links) > 0:
            result += "\n<b>Ссылки, где можно посмотреть:</b>\n"
            for link in links:
                result += hlink(f"● {link}\n", links[link])
        else:
            result += "\n<b>Ссылок, где посмотреть, я не нашел</b> 😔\n"
        try:
            db.update_user_stats(username, film_name)
            db.update_user_history(username, row_user_request)
        except Exception:
            pass
        return result
