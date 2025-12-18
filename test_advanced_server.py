import enum
import os
from dataclasses import dataclass

from typing import List

from context_helper import ctx, Context
from graphql_api import GraphQLAPI, field

from typing import Optional

from sqlalchemy import create_engine
from sqlalchemy_gql import GraphQLSQLAlchemyMixin
from sqlmodel import Field, SQLModel, Session, select, col

from graphql_http_server import GraphQLHTTPServer


class Note(GraphQLSQLAlchemyMixin, SQLModel, table=True):
    id: int = Field(primary_key=True)
    title: str = ""
    note: str = ""

    @field(mutable=True)
    def update(self, title: str = None, note: str = None) -> 'Note':
        if title is not None:
            self.title = title

        if note is not None:
            self.note = note

        return self

    @field(mutable=True)
    def delete(self) -> bool:
        ctx.session.delete(self)
        return True


class OrderByDirection(enum.Enum):
    asc = "asc"
    desc = "desc"

@dataclass
class OrderBy:
    key: str
    direction: OrderByDirection = OrderByDirection.asc

@dataclass
class NoteFilter:
    ids: List[int] = None
    title: str = ""

class Notes:

    @field(mutable=True)
    def create_note(self, title: str, note: str) -> Note:
        note = Note(title=title, note=note)
        ctx.session.add(note)

        return note

    @field
    def all_notes(
        self,
        order_by: List[OrderBy] = None,
        filter: NoteFilter = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[Note]:
        """
        Find `Notes`
        """
        query = select(Note)

        if filter and filter.ids:
            query = query.where(col(Note.id).in_(filter.ids))

        if filter and filter.title:
            query = query.where(col(Note.title).contains(filter.title))

        if order_by:
            for _order_by in order_by:
                c = getattr(Note,_order_by.key)
                if _order_by.direction == OrderByDirection.asc:
                    c = c.asc()
                else:
                    c = c.desc()
                query = query.order_by(c)

        return ctx.session.exec(query.limit(limit).offset(offset)).all()

    @field
    def note(self, id: int = None, title: str = None) -> Optional[Note]:
        """
        Title or id must be an exact match.
        """
        if id:
            return ctx.session.exec(select(Note).where(Note.id==id)).one()
        if title:
            return ctx.session.exec(select(Note).where(Note.title==title)).one()


path = os.path.join(os.path.dirname(__file__), './example.graphql')
with open(path, mode='r') as file:
    default_query = file.read()

engine = create_engine("sqlite://")

SQLModel.metadata.create_all(engine)

server = GraphQLHTTPServer.from_api(
    api=GraphQLAPI(root_type=Notes),
    graphiql_default_query=default_query
)


def main(request):
    with Session(engine) as session:
        with Context(session=session):
            response = server.dispatch(request=request)
        session.commit()

    return response


if __name__ == "__main__":
    server.run(main=main, port=3500)