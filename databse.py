import sqlite3
from pypika import Query, Table
import typing as tp


class DataBaseHandler:
    def __init__(self, sqlite_database_name: str):

        self._connection = sqlite3.connect(sqlite_database_name)

        self._cursor = self._connection.cursor()

        self._cursor.execute("CREATE TABLE IF NOT EXISTS history (user TEXT, request TEXT)")
        self._cursor.execute("CREATE TABLE IF NOT EXISTS stats (user TEXT, film TEXT, showing INTEGER)")

        self._connection.commit()

    def update_user_history(self, username: str, user_request: str) -> None:
        """
        Checks whether there has already been such a request from the user, if not, then adds it to the database.
        :param username: telegram username
        :param user_request:
        :return:
        """
        user_history: tp.Sequence[tuple[str]] | None = self.get_user_history(username)
        if user_history is not None and (user_request,) in user_history:
            return None
        query = Query.into(Table("history")).columns("user", "request").insert(username, user_request)
        self._cursor.execute(str(query))
        self._connection.commit()

    def get_user_history(self, username: str) -> list[tuple[str]]:
        """
        Retrieves all user queries from the database.
        :param username: telegram username
        :return: a list of all requests received from the user or None if the user hasn't searched yet
        """
        history = Table("history")
        query = Query.from_(history).select("request").where(history.user == username)
        self._cursor.execute(str(query))
        return self._cursor.fetchall()

    def update_user_stats(self, username: str, showed_film_name: str) -> None:
        """
        Checks if such a movie has already been offered to the user, if yes,
        then updates the impression counter for this movie,
        otherwise adds a new record to the database (impression counter = 1).
        :param username: telegram username
        :param showed_film_name: movie title on imdb that was suggested to the user
        :return:
        """
        user_stats: tp.Sequence[tuple[str, int]] | None = self.get_user_stats(username)
        if user_stats is not None:
            for film_name, film_showing in user_stats:
                if film_name == showed_film_name:
                    table = Table("stats")
                    query = Query.update(table)\
                        .set("showing", film_showing + 1)\
                        .where(table.user == username and table.film == showed_film_name)
                    self._cursor.execute(str(query))
                    self._connection.commit()
                    return None
            table = Table("stats")
            query = Query.into(table).columns("user", "film", "showing").insert(username, showed_film_name, 1)
            self._cursor.execute(str(query))
            self._connection.commit()

    def get_user_stats(self, username: str) -> list[tuple[str, int]]:
        """
        :param username: telegram username
        :return: returns impression statistics for the given user in tuple format (movie title, number of impressions)
        """
        table = Table("stats")
        query = Query.from_(table).select("film", "showing").where(table.user == username)
        self._cursor.execute(str(query))
        return self._cursor.fetchall()
