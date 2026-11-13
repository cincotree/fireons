PLANNERS = [
    {
        "name": "Asha Fictional",
        "firm": "Sample Planning Studio",
        "website": "https://www.sampleplanning.example.com/?utm_source=FOI&utm_medium=display",
        "languages": "(Hindi, Tamil)",
    },
    {
        "name": "Ravi Imaginary",
        "firm": "Ravi Imaginary",
        "website": "https://raviplans.example.org",
        "languages": "(Marathi)",
    },
    {
        "name": "Meera Placeholder",
        "firm": "Placeholder Wealth (*Stopped taking new clients from Mar 1, 2024)",
        "website": "https://placeholderwealth.example.com/about/",
        "languages": "(Hindi, Gujarati, Marathi)",
    },
]

BLURBS = [
    ("FEE-ONLY", "Compensated only with the fee clients pay directly."),
    ("FLAT FEE", "Charging a flat fee."),
]


def _blurb(title: str, text: str) -> str:
    return (
        '<div role="listitem"><div class="wixui-repeater__item">'
        f'<h4 class="font_4">{title}</h4><p class="font_7">{text}</p></div></div>'
    )


def _planner(planner: dict) -> str:
    website = planner.get("website")
    button = (
        f'<a data-testid="linkElement" href="{website.replace("&", "&amp;")}" aria-label="Website">'
        '<span>Website</span></a>'
        if website
        else ""
    )
    languages = f'<p class="font_7">{planner["languages"]}</p>' if planner.get("languages") else ""
    name = f'<h4 class="font_4"><span>{planner["name"]}</span></h4>' if planner.get("name") else "<h4></h4>"
    return (
        '<div role="listitem"><div class="wixui-repeater__item">'
        f'{name}<h6 class="font_6">{planner["firm"]}</h6>{button}{languages}'
        "</div></div>"
    )


def render_listing(planners: list[dict] = PLANNERS) -> str:
    blurbs = "".join(_blurb(*blurb) for blurb in BLURBS)
    cards = "".join(_planner(planner) for planner in planners)
    return f"<html><body><section>{blurbs}</section><section>{cards}</section></body></html>"
