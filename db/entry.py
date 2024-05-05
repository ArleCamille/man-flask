from . import BaseEntry
from sqlalchemy import PrimaryKeyConstraint, UniqueConstraint, Engine
from sqlalchemy import ForeignKey
from sqlalchemy import select, or_
from sqlalchemy.orm import Mapped, mapped_column, Session
from sqlalchemy.dialects.sqlite import insert as upsert
from sys import stderr
from typing import Optional

class ManEntry(BaseEntry):
    __tablename__ = 'section'

    section: Mapped[str]       = mapped_column(index=True, nullable=False)
    path_section: Mapped[str]  = mapped_column(index=True, nullable=False)
    manual: Mapped[str]        = mapped_column(index=True, nullable=False)
    man_extension: Mapped[str] = mapped_column(nullable=True)

    __table_args__ = (
        PrimaryKeyConstraint('path_section', 'manual'),
        UniqueConstraint('section', 'manual'),
    )

    def __repr__(self) -> str:
        return f"ManEntry(section='{self.section}',path_section=" \
            f"'{self.path_section}',manual='{self.manual}'," \
            f"man_extension='{self.man_extension}')"

    def __str__(self) -> str:
        suffix_string = ''
        if self.man_extension is not None:
            suffix_string = f'.{self.man_extension}'
        return f'man{self.path_section}/{self.manual}.{self.section}' + \
            suffix_string

    @staticmethod
    def create_section(engine: Engine, /, section: str, manual: str, *,
                       path_section: Optional[str],
                       man_extension: Optional[str]):
        if path_section is None:
            path_section = section
        with Session(engine) as session:
            # TODO: more concise way?
            stmt = upsert(ManEntry).values({
                'section': section,
                'path_section': path_section,
                'manual': manual,
                'man_extension': man_extension,
            })
            stmt = stmt.on_conflict_do_update(set_=dict(
                section=stmt.excluded.section,
                man_extension=stmt.excluded.man_extension,
            ))
            session.execute(stmt)
            session.commit()

    @staticmethod
    def list_all_sections(engine: Engine, /) -> list[str]:
        with Session(engine) as session:
            query  = select(ManEntry.section)
            result = set(session.scalars(query).all())
            query  = select(ManEntry.path_section)
            result = result.union(session.scalars(query).all())

            return sorted(list(result))

    @staticmethod
    def find_entry(engine: Engine, /, manual: str, *, section: Optional[str]):
        with Session(engine) as session:
            query = select(ManEntry).where(ManEntry.manual == manual) \
                .order_by(ManEntry.section.asc)
            if section is not None:
                query = query.where(or_(ManEntry.section == section,
                                        ManEntry.path_section == section))
            return session.scalars(query).first()

__all__ = ['ManEntry']