from pathlib import Path

FIXTURES_DIR = Path(__file__).parent / "sebi_ria"

GOOD_RECORDS = [
    {
        "name": "Example Advisers Private Limited",
        "reg": "INA000000001",
        "email": "compliance@example.com",
        "phone": "910000000001",
        "fax": "910000000002",
        "address": "Unit 1, Sample Plaza, Sample Road, MUMBAI, MAHARASHTRA, 400001",
        "contact": "Test Person One",
        "correspondence": "Unit 1, Sample Plaza, Sample Road, MUMBAI, MAHARASHTRA, 400001",
        "validity": "Dec 22, 2022 - Perpetual",
    },
    {
        "name": "Asha Fictional",
        "reg": "INA000000002",
        "address": "1 Test Lane, BENGALURU, KARNATAKA, 560001",
        "contact": "Asha Fictional",
        "validity": "Mar 05, 2019 - Mar 04, 2024",
    },
    {
        "name": "Ravi Imaginary",
        "reg": "INA000000003",
        "email": "Ravi.Imaginary@Example.com",
        "phone": "910000000003",
        "address": "5 Nowhere Street, NAGPUR CITY, MAHARASHTRA, NAGPUR, MAHARASHTRA, 440022",
        "contact": "Ravi Imaginary",
        "correspondence": "5 Nowhere Street, NAGPUR CITY, MAHARASHTRA, NAGPUR, MAHARASHTRA, 440022",
        "validity": "Jan 06, 2025 - Perpetual",
    },
    {
        "name": "Sample Wealth LLP",
        "reg": "INA000000004",
        "email": "hello@example.com",
        "address": "Plot 9, Test Colony, 110001",
        "contact": "Sample Contact",
        "validity": "Jun 30, 2021 - Perpetual",
    },
    {
        "name": "Meera Placeholder",
        "reg": "INA000000006",
        "phone": "910000000006",
        "address": "12 Test Road, DELHI, DELHI, 110001",
        "contact": "Meera Placeholder",
        "validity": "Aug 11, 2020 - Perpetual",
    },
    {
        "name": "Kiran Fixture",
        "reg": "INA000000007",
        "email": "kiran@example.com",
        "address": "7 Sample Street, Chennai, Tamil Nadu, 600001",
        "contact": "Kiran Fixture",
        "validity": "Feb 14, 2023 - Perpetual",
    },
]

BROKEN_RECORD = {
    "name": "Broken Validity Adviser",
    "reg": "INA000000005",
    "address": "3 Broken Street, PUNE, MAHARASHTRA, 411001",
    "contact": "Broken Contact",
    "validity": "Sometime in 2020",
}

DUPLICATE_OF_FIRST = GOOD_RECORDS[0]

SAMPLE_RECORDS = [
    GOOD_RECORDS[0],
    GOOD_RECORDS[1],
    GOOD_RECORDS[2],
    GOOD_RECORDS[3],
    BROKEN_RECORD,
    GOOD_RECORDS[4],
    GOOD_RECORDS[5],
    DUPLICATE_OF_FIRST,
]


def _encode_entities(value: str) -> str:
    return value.replace("@", "&#64;").replace(".", "&#46;")


def _fields(record: dict) -> list[tuple[str, str]]:
    fields = [("Name", record["name"], "varun-text"), ("Registration No.", record["reg"], "")]
    optional = [
        ("E-mail", record.get("email")),
        ("Telephone", record.get("phone")),
        ("Fax No.", record.get("fax")),
        ("Address", record.get("address")),
        ("Contact Person", record.get("contact")),
        ("Correspondence Address", record.get("correspondence")),
        ("Validity", record.get("validity")),
    ]
    for title, value in optional:
        if value:
            fields.append((title, value, ""))
    return fields


def _card(record: dict, indented: bool) -> str:
    rows = []
    for title, value, css in _fields(record):
        shown = _encode_entities(value) if title == "E-mail" else value
        value_class = f"value {css}".strip()
        if indented:
            rows.append(
                f'                                                        <div class="card-view">'
                f'<div class="title"><span> {title} </span></div>'
                f'<div class="{value_class}"><span>{shown}</span></div></div>\n'
                f"                                                    \n"
            )
        else:
            rows.append(
                f"<div class='card-view'><div class='title'><span>{title}</span></div>"
                f"<div class='{value_class}'><span>{shown}</span></div></div>"
            )
    if indented:
        return (
            '                                            <div class="fixed-table-body card-table">\n'
            '                                                <div class="card-table-left">\n'
            + "".join(rows)
            + "                                                </div>\n"
            "                                            </div>\n"
        )
    return "<div class='fixed-table-body card-table'><div class='card-table-left'>" + "".join(rows) + "</div></div>"


def _pagination(start: int, end: int, total: int, indented: bool) -> str:
    if indented:
        return (
            '                            <div class="pagination">\n'
            '                                <div class="pagination_inner">\n'
            f"                                    <p>{start} to {end} of {total} records</p>\n"
            "                                </div>\n"
            "                            </div><br/><br/>\n"
        )
    return (
        "<div class='pagination'><div class='pagination_inner'>"
        f"<p>{start} to {end} of {total} records</p></div></div><br/><br/>"
    )


def render_first_page(records: list[dict], start: int, end: int, total: int) -> str:
    cards = "".join(_card(record, indented=True) for record in records)
    return (
        "<!DOCTYPE html>\n<html lang=\"en\">\n<head><title>SEBI | Investment Adviser</title></head>\n"
        '<body id="mainContainer">\n<form name="otherForm" method="post">\n'
        '<div id="ajax_cat">\n'
        + _pagination(start, end, total, indented=True)
        + cards
        + "</div>\n</form>\n</body>\n</html>\n"
    )


def render_ajax_page(records: list[dict], start: int, end: int, total: int) -> str:
    return _pagination(start, end, total, indented=False) + "".join(
        _card(record, indented=False) for record in records
    )


def paginate(records: list[dict], page_size: int) -> list[tuple[list[dict], int, int]]:
    total = len(records)
    pages = []
    for offset in range(0, total, page_size):
        chunk = records[offset : offset + page_size]
        pages.append((chunk, offset + 1, offset + len(chunk)))
    return pages


def build_pages(records: list[dict], page_size: int = 3) -> list[str]:
    total = len(records)
    rendered = []
    for index, (chunk, start, end) in enumerate(paginate(records, page_size)):
        renderer = render_first_page if index == 0 else render_ajax_page
        rendered.append(renderer(chunk, start, end, total))
    return rendered


def write_fixtures() -> None:
    FIXTURES_DIR.mkdir(parents=True, exist_ok=True)
    names = ["listing_page_1.html", "ajax_page_2.html", "ajax_page_3.html"]
    for name, html in zip(names, build_pages(SAMPLE_RECORDS, page_size=3)):
        (FIXTURES_DIR / name).write_text(html, encoding="utf-8")


if __name__ == "__main__":
    write_fixtures()
