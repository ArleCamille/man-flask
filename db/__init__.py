from sqlalchemy.orm import DeclarativeBase

class BaseEntry(DeclarativeBase):
    pass

# import actual schemas
from .entry import ManEntry

__all__ = ['BaseEntry', 'ManEntry']