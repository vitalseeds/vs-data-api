import pathlib
import os
from typing import List, Literal, Optional, Tuple
from pydantic_xml import BaseXmlModel, attr, element, wrapped


class BaseTable(BaseXmlModel):
    table_name: Optional[str] = attr(name="name")


class BaseTableCatalog(BaseXmlModel):
    tables: List[BaseTable] = element(tag="BaseTable")


class File(BaseXmlModel):
    table_catalog: BaseTable = element(tag="BaseTableCatalog")


class FMPReport(BaseXmlModel):
    file: File = element(tag="File")


def parse_database_design_report(path):
    xml_doc = pathlib.Path(path).read_text(encoding="utf-16")
    return FMPReport.from_xml(xml_doc)


def test_duplicate_fmdb_schema():
    ddr = os.environ[]
    tables = parse_database_design_report(ddr)
    from objexplore import explore
    explore(tables)
    import pudb; pu.db
    print(tables)
