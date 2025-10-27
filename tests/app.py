from graphql_api import GraphQLAPI
from graphql_http import GraphQLHTTP
from enum import Enum
from typing import Optional
from datetime import datetime

api = GraphQLAPI()


class UserRole(Enum):
    READER = "READER"
    AUTHOR = "AUTHOR"
    LIBRARIAN = "LIBRARIAN"
    ADMIN = "ADMIN"


class BookStatus(Enum):
    AVAILABLE = "AVAILABLE"
    CHECKED_OUT = "CHECKED_OUT"
    RESERVED = "RESERVED"
    MAINTENANCE = "MAINTENANCE"


@api.type
class Address:
    def __init__(self, street: str, city: str, state: str, zip_code: str, country: str = "USA"):
        self._street = street
        self._city = city
        self._state = state
        self._zip_code = zip_code
        self._country = country

    @api.field
    def street(self) -> str:
        return self._street

    @api.field
    def city(self) -> str:
        return self._city

    @api.field
    def state(self) -> str:
        return self._state

    @api.field
    def zip_code(self) -> str:
        return self._zip_code

    @api.field
    def country(self) -> str:
        return self._country

    @api.field
    def full_address(self) -> str:
        return f"{self._street}, {self._city}, {self._state} {self._zip_code}, {self._country}"


@api.type
class User:
    def __init__(self, id: str, name: str, email: str, role: UserRole, address: Optional[Address] = None):
        self._id = id
        self._name = name
        self._email = email
        self._role = role
        self._address = address

    @api.field
    def id(self) -> str:
        return self._id

    @api.field
    def name(self) -> str:
        return self._name

    @api.field
    def email(self) -> str:
        return self._email

    @api.field
    def role(self) -> UserRole:
        return self._role

    @api.field
    def address(self) -> Optional[Address]:
        return self._address


@api.type
class Genre:
    def __init__(self, id: str, name: str, description: str):
        self._id = id
        self._name = name
        self._description = description

    @api.field
    def id(self) -> str:
        return self._id

    @api.field
    def name(self) -> str:
        return self._name

    @api.field
    def description(self) -> str:
        return self._description


@api.type
class Publisher:
    def __init__(self, id: str, name: str, founded_year: int, address: Address):
        self._id = id
        self._name = name
        self._founded_year = founded_year
        self._address = address

    @api.field
    def id(self) -> str:
        return self._id

    @api.field
    def name(self) -> str:
        return self._name

    @api.field
    def founded_year(self) -> int:
        return self._founded_year

    @api.field
    def address(self) -> Address:
        return self._address

    @api.field
    def age(self) -> int:
        return datetime.now().year - self._founded_year


@api.type
class Author:
    def __init__(self, id: str, user: User, bio: str, birth_year: Optional[int] = None):
        self._id = id
        self._user = user
        self._bio = bio
        self._birth_year = birth_year

    @api.field
    def id(self) -> str:
        return self._id

    @api.field
    def user(self) -> User:
        return self._user

    @api.field
    def bio(self) -> str:
        return self._bio

    @api.field
    def birth_year(self) -> Optional[int]:
        return self._birth_year

    @api.field
    def age(self) -> Optional[int]:
        if self._birth_year:
            return datetime.now().year - self._birth_year
        return None


@api.type
class Review:
    def __init__(self, id: str, reviewer: User, rating: int, comment: str, book_id: str):
        self._id = id
        self._reviewer = reviewer
        self._rating = rating
        self._comment = comment
        self._book_id = book_id

    @api.field
    def id(self) -> str:
        return self._id

    @api.field
    def reviewer(self) -> User:
        return self._reviewer

    @api.field
    def rating(self) -> int:
        return self._rating

    @api.field
    def comment(self) -> str:
        return self._comment

    @api.field
    def book_id(self) -> str:
        return self._book_id


@api.type
class Book:
    def __init__(self, id: str, title: str, author: Author, isbn: str,
                 publisher: Publisher, genres: list[Genre], status: BookStatus = BookStatus.AVAILABLE,
                 page_count: Optional[int] = None, publication_year: Optional[int] = None):
        self._id = id
        self._title = title
        self._author = author
        self._isbn = isbn
        self._publisher = publisher
        self._genres = genres
        self._status = status
        self._page_count = page_count
        self._publication_year = publication_year

    @api.field
    def id(self) -> str:
        return self._id

    @api.field
    def title(self) -> str:
        return self._title

    @api.field
    def author(self) -> Author:
        return self._author

    @api.field
    def isbn(self) -> str:
        return self._isbn

    @api.field
    def publisher(self) -> Publisher:
        return self._publisher

    @api.field
    def genres(self) -> list[Genre]:
        return self._genres

    @api.field
    def status(self) -> BookStatus:
        return self._status

    @api.field
    def page_count(self) -> Optional[int]:
        return self._page_count

    @api.field
    def publication_year(self) -> Optional[int]:
        return self._publication_year

    @api.field
    def reviews(self) -> list[Review]:
        # In a real app, this would query a database
        # For demo purposes, return mock reviews
        return [
            Review("rev1", User("u2", "Alice Reader", "alice@example.com", UserRole.READER),
                   5, f"Great book! Really enjoyed {self._title}.", self._id),
            Review("rev2", User("u3", "Bob Critic", "bob@example.com", UserRole.READER),
                   4, f"{self._title} was a solid read with good character development.", self._id)
        ]


@api.type
class Library:
    def __init__(self, id: str, name: str, address: Address, established_year: int):
        self._id = id
        self._name = name
        self._address = address
        self._established_year = established_year

    @api.field
    def id(self) -> str:
        return self._id

    @api.field
    def name(self) -> str:
        return self._name

    @api.field
    def address(self) -> Address:
        return self._address

    @api.field
    def established_year(self) -> int:
        return self._established_year

    @api.field
    def books(self) -> list[Book]:
        # In a real app, this would query a database
        return get_sample_books()

    @api.field
    def available_books(self) -> list[Book]:
        return [book for book in self.books() if book.status() == BookStatus.AVAILABLE]


def get_sample_books() -> list[Book]:
    # Create sample data
    address_ny = Address("123 Publisher St", "New York", "NY", "10001")
    address_user = Address("456 Reader Ave", "Boston", "MA", "02101")

    publisher = Publisher("pub1", "Penguin Random House", 1927, address_ny)

    fiction_genre = Genre("genre1", "Fiction", "Literary fiction and novels")
    dystopian_genre = Genre("genre2", "Dystopian",
                            "Dystopian and post-apocalyptic fiction")
    classic_genre = Genre("genre3", "Classic", "Classic literature")

    user_fitzgerald = User("u1", "F. Scott Fitzgerald",
                           "fscott@example.com", UserRole.AUTHOR, address_user)
    author_fitzgerald = Author(
        "auth1", user_fitzgerald, "American novelist and short story writer", 1896)

    user_orwell = User("u4", "George Orwell",
                       "gorwell@example.com", UserRole.AUTHOR)
    author_orwell = Author("auth2", user_orwell,
                           "English novelist and essayist", 1903)

    book1 = Book(
        "book1", "The Great Gatsby", author_fitzgerald, "978-0-7432-7356-5",
        publisher, [fiction_genre,
                    classic_genre], BookStatus.AVAILABLE, 180, 1925
    )

    book2 = Book(
        "book2", "1984", author_orwell, "978-0-452-28423-4",
        publisher, [fiction_genre, dystopian_genre,
                    classic_genre], BookStatus.CHECKED_OUT, 328, 1949
    )

    return [book1, book2]


@api.type(is_root_type=True)
class HelloWorld:

    @api.field
    def hello_world(self, name: str) -> str:
        return f"Hello {name}!"

    @api.field(mutable=True)
    def update_user(self, id: str, name: str, email: str) -> Optional[User]:
        return None

    @api.field(mutable=True)
    def update_book(self, id: str, title: str, author: Author, isbn: str,
                    publisher: Publisher, genres: list[Genre], status: BookStatus = BookStatus.AVAILABLE,
                    page_count: Optional[int] = None, publication_year: Optional[int] = None) -> Optional[Book]:
        return None

    @api.field
    def user(self) -> User:
        address = Address("789 Main St", "Springfield", "IL", "62701")
        return User("123", "John Doe", "john@example.com", UserRole.READER, address)

    @api.field
    def books(self) -> list[Book]:
        return get_sample_books()

    @api.field
    def libraries(self) -> list[Library]:
        address_lib1 = Address("100 Library Way", "Boston", "MA", "02102")
        address_lib2 = Address("200 Book Blvd", "Cambridge", "MA", "02138")

        return [
            Library("lib1", "Boston Public Library", address_lib1, 1895),
            Library("lib2", "Harvard Library", address_lib2, 1638)
        ]

    @api.field
    def authors(self) -> list[Author]:
        books = get_sample_books()
        return [book.author() for book in books]

    @api.field
    def genres(self) -> list[Genre]:
        return [
            Genre("genre1", "Fiction", "Literary fiction and novels"),
            Genre("genre2", "Dystopian", "Dystopian and post-apocalyptic fiction"),
            Genre("genre3", "Classic", "Classic literature"),
            Genre("genre4", "Science Fiction",
                  "Science fiction and speculative fiction"),
            Genre("genre5", "Mystery", "Mystery and thriller novels")
        ]

    @api.field
    def users_by_role(self, role: UserRole) -> list[User]:
        all_users = [
            User("u1", "F. Scott Fitzgerald",
                 "fscott@example.com", UserRole.AUTHOR),
            User("u2", "Alice Reader", "alice@example.com", UserRole.READER),
            User("u3", "Bob Critic", "bob@example.com", UserRole.READER),
            User("u4", "George Orwell", "gorwell@example.com", UserRole.AUTHOR),
            User("u5", "Library Admin", "admin@library.com", UserRole.LIBRARIAN)
        ]
        return [user for user in all_users if user.role() == role]


example_query = "query HelloQuery($name: String!){  helloWorld(name: $name) }"

server = GraphQLHTTP.from_api(
    api=api,
    graphiql_example_query=example_query,
    allow_cors=True,
)

if __name__ == "__main__":
    server.run(port=3501)
