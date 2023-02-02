from typing import Optional

from sqlmodel import Field, Session, SQLModel, create_engine
import sqlalchemy
from datetime import date

import pypyodbc

from sqlalchemy.connectors.pyodbc import PyODBCConnector


# class PyPyODBCConnector(PyODBCConnector):
#     driver = "pypyodbc"

#     @classmethod
#     def dbapi(cls):
#         return __import__("pypyodbc")


class Acquisitions(SQLModel, table=True):
    # table_name = "acquisitions"
    sku: str = Field(default=None, primary_key=True)
    crop: str
    wc_product_id: int


class PacketingBatches(SQLModel, table=True):
    # table_name = "packeting_batches"
    batch_number: int = Field(default=None, primary_key=True)
    awaiting_upload: Optional[str]
    sku: int
    skufk: int
    packets: int
    to_pack: int
    pack_date: date


# class Hero(SQLModel, table=True):
#     id: Optional[int] = Field(default=None, primary_key=True)
#     name: str
#     secret_name: str
#     age: Optional[int] = None


# hero_1 = Hero(name="Deadpond", secret_name="Dive Wilson")
# hero_2 = Hero(name="Spider-Boy", secret_name="Pedro Parqueador")
# hero_3 = Hero(name="Rusty-Man", secret_name="Tommy Sharp", age=48)


# e = create_engine("mssql+pyodbc://DSN=vs_stock;UID=vs_data;PWD=1234", module=pypyodbc)
# e = create_engine("mssql+pyodbc://DSN=vs_stock;UID=vs_data;PWD=1234")
# c = e.connect()
# sqlalchemy.dialects

driver = "FileMaker+ODBC"

username = "vs_data"
password = "1234"
dsn = "vs_stock"
database = "vs_db"
engine_stmt = f"mssql+pyodbc://{username}:{password}@{dsn}/{database}?driver={driver}"

# engine = sqlalchemy.create_engine(engine_stmt, module=pypyodbc)
engine = sqlalchemy.create_engine(
    "mssql+pyodbc://DSN=vs_stock;UID=vs_data;PWD=1234", module=pypyodbc
)
SQLModel.metadata.create_all(engine)

# # https://stackoverflow.com/questions/4493614/sqlalchemy-equivalent-of-pyodbc-connect-string-using-freetds
# # https://docs.sqlalchemy.org/en/13/core/engines.html#microsoft-sql-server
# def connect():
#     pypyodbc.connect(
#         # "DRIVER={FreeTDS};Server=my.db.server;Database=mydb;UID=myuser;PWD=mypwd;TDS_Version=8.0;Port=1433;"
#         "DSN=vs_stock;UID=vs_data;PWD=1234"
#     )


# # engine = sqlalchemy.create_engine("mssql://", creator=connect)
# engine = sqlalchemy.create_engine(
#     "mssql+pyodbc://DSN=vs_stock;UID=vs_data;PWD=1234",
#     echo=True,
#     # creator=connect,
#     module=pypyodbc,
# )

# # engine = create_engine("sqlite:///database.db")

# SQLModel.metadata.create_all(engine)

# from pudb import set_trace

# set_trace()

# with Session(engine) as session:
#     session.add(hero_1)
#     session.add(hero_2)
#     session.add(hero_3)
#     session.commit()
