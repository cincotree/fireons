import json

CITIES = ["Testville", "TESTVILLE", "Samplepur", "Emptytown"]

TESTVILLE_ROWS = [
    {
        "ARN": "100001",
        "ARNHolderName": "Example Distributors Private Limited",
        "Address": "Unit 1 Sample Plaza Sample Road Mumbai Maharashtra 400001",
        "ARNValidFrom": "2023-04-01T00:00:00.000Z",
        "ARNValidTill": "2028-03-31T00:00:00.000Z",
        "Pin": "400001",
        "City": "Testville",
        "KYDCompliant": "Y",
        "EUIN": "E000001",
        "SIF_Validity_From": None,
        "SIF_Validity_to": None,
        "TelephoneNumber_O": "9100000001",
        "TelephoneNumber_R": "9100000002",
        "Email": "Desk@Example.com",
    },
    {
        "ARN": "42",
        "ARNHolderName": "Asha Fictional",
        "Address": "1 Test Lane",
        "ARNValidFrom": "2019-01-10T00:00:00.000Z",
        "ARNValidTill": "2024-01-09T00:00:00.000Z",
        "Pin": "560001",
        "City": "Testville",
        "KYDCompliant": "N",
        "EUIN": None,
        "SIF_Validity_From": "2025-01-01T00:00:00.000Z",
        "SIF_Validity_to": "2028-01-01T00:00:00.000Z",
        "TelephoneNumber_O": "",
        "TelephoneNumber_R": "9100000003",
        "Email": "",
    },
    {
        "ARN": "100003",
        "ARNHolderName": "Ravi Imaginary",
        "Address": "5 Nowhere Street",
        "ARNValidFrom": "2022-06-01T00:00:00.000Z",
        "ARNValidTill": None,
        "Pin": "0",
        "City": "Testville",
        "KYDCompliant": "Y",
        "EUIN": "E000003",
        "SIF_Validity_From": None,
        "SIF_Validity_to": None,
        "TelephoneNumber_O": "9100000004",
        "TelephoneNumber_R": "9100000004",
        "Email": None,
    },
]

SAMPLEPUR_ROWS = [
    {
        "ARN": "100004",
        "ARNHolderName": "Sample Wealth LLP",
        "Address": "Plot 9 Test Colony",
        "ARNValidFrom": "2021-06-30T00:00:00.000Z",
        "ARNValidTill": "2026-06-29T00:00:00.000Z",
        "Pin": "682001",
        "City": "Samplepur",
        "KYDCompliant": "Y",
        "EUIN": "E000004",
        "SIF_Validity_From": None,
        "SIF_Validity_to": None,
        "TelephoneNumber_O": "9100000005",
        "TelephoneNumber_R": "",
        "Email": "hello@example.com",
    },
    {
        "ARN": "100005",
        "ARNHolderName": "Meera Placeholder",
        "Address": "12 Test Road",
        "ARNValidFrom": "2020-08-11T00:00:00.000Z",
        "ARNValidTill": "2025-08-10T00:00:00.000Z",
        "Pin": "110001",
        "City": "Samplepur",
        "KYDCompliant": "Y",
        "EUIN": "E000005",
        "SIF_Validity_From": None,
        "SIF_Validity_to": None,
        "TelephoneNumber_O": "9100000006",
        "TelephoneNumber_R": "",
        "Email": "meera@example.com",
    },
]

BROKEN_ROW = {
    "ARN": "100006",
    "ARNHolderName": "Broken Validity Distributor",
    "Address": "3 Broken Street",
    "ARNValidFrom": "sometime in 2020",
    "ARNValidTill": None,
    "Pin": "411001",
    "City": "Samplepur",
}

ROWS_BY_CITY = {"testville": TESTVILLE_ROWS, "samplepur": SAMPLEPUR_ROWS, "emptytown": []}
ALL_GOOD_ROWS = TESTVILLE_ROWS + SAMPLEPUR_ROWS


def render_locate_page(cities: list[str]) -> str:
    entries = ",".join(json.dumps({"City": c}, separators=(",", ":")) for c in cities)
    pincodes = ",".join(json.dumps({"Pin_x0020_Code": p}, separators=(",", ":")) for p in ("110001", "400001"))
    flight = f'{{"initialCities":[{entries}],"initialPincodes":[{pincodes}]}}'
    escaped = flight.replace("\\", "\\\\").replace('"', '\\"')
    return f'<html><body><script>self.__next_f.push([1,"{escaped}"])</script></body></html>'


def render_api_page(rows_by_city: dict[str, list[dict]], city: str, page: int, page_size: int) -> dict:
    rows = rows_by_city.get(city.casefold(), [])
    start = (page - 1) * page_size
    page_count = max(-(-len(rows) // page_size), 0)
    return {
        "data": rows[start : start + page_size],
        "meta": {"page": page, "pageSize": page_size, "total": len(rows), "pageCount": page_count},
    }
