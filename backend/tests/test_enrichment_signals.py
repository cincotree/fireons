import pytest

from enrichment.domains import candidate_domains, domain_from_email, is_public_firm_domain
from enrichment.signals import Confidence, Location, SignalType, detect_signals

URL = "https://firm.example.com/"


def page(title="", body="", meta="", extra_head=""):
    description = f'<meta name="description" content="{meta}">' if meta else ""
    return f"<html><head><title>{title}</title>{description}{extra_head}</head><body>{body}</body></html>"


def by_type(signals):
    return {s.signal_type: s for s in signals}


def test_nri_in_title_is_high_confidence_with_the_matched_text():
    signals = detect_signals(URL, page(title="Wealth advisory for NRIs | Sample Advisers"))

    signal = by_type(signals)[SignalType.NRI_MENTION]
    assert signal.confidence == Confidence.HIGH
    assert signal.location == Location.TITLE
    assert "NRIs" in signal.matched_text


def test_nri_in_a_heading_is_high_and_in_navigation_links_too():
    heading = detect_signals(URL, page(body="<h2>Investment services for Non-Resident Indians</h2>"))
    link = detect_signals(URL, page(body='<nav><a href="/nri">NRI Services</a></nav>'))

    assert by_type(heading)[SignalType.NRI_MENTION].confidence == Confidence.HIGH
    assert by_type(link)[SignalType.NRI_MENTION].location == Location.LINK


def test_single_body_mention_is_medium_with_surrounding_context():
    body = "<p>" + "We help families plan. " * 8 + "We also serve NRI clients abroad. " + "Call us today. " * 8 + "</p>"

    signals = detect_signals(URL, page(body=body))

    signal = by_type(signals)[SignalType.NRI_MENTION]
    assert signal.confidence == Confidence.MEDIUM
    assert signal.location == Location.BODY
    assert "serve NRI clients" in signal.matched_text
    assert signal.matched_text.startswith("...")


def test_body_mention_upgrades_to_high_when_the_page_has_several_signal_types():
    body = "<p>NRI investors can invest through NRE and NRO accounts with full repatriation.</p>"

    signals = by_type(detect_signals(URL, page(body=body)))

    assert signals[SignalType.NRI_MENTION].confidence == Confidence.HIGH
    assert signals[SignalType.NRI_ACCOUNT].confidence == Confidence.HIGH


def test_weak_terms_alone_are_low_in_body_and_medium_when_prominent():
    body = "<p>We are familiar with FEMA rules for clients.</p>"
    prominent = "<h2>Repatriation made simple</h2>"

    assert by_type(detect_signals(URL, page(body=body)))[SignalType.REPATRIATION].confidence == Confidence.LOW
    assert by_type(detect_signals(URL, page(body=prominent)))[SignalType.REPATRIATION].confidence == Confidence.MEDIUM


def test_negated_mention_is_downgraded_to_low():
    signals = detect_signals(URL, page(title="Our services are not available for NRIs"))

    assert by_type(signals)[SignalType.NRI_MENTION].confidence == Confidence.LOW


def test_meta_description_counts_as_prominent():
    signals = detect_signals(URL, page(meta="Mutual funds and financial planning for overseas Indians"))

    signal = by_type(signals)[SignalType.NRI_MENTION]
    assert (signal.location, signal.confidence) == (Location.META, Confidence.HIGH)


def test_scripts_and_styles_are_ignored():
    body = "<script>var label = 'NRI offers';</script><style>.nri { color: red }</style><p>Hello</p>"

    assert detect_signals(URL, page(body=body)) == []


def test_lowercase_nri_inside_words_does_not_match():
    assert detect_signals(URL, page(body="<p>Our nrihub tool and the Nrity dance club</p>")) == []


def test_page_without_signals_and_empty_html_return_nothing():
    assert detect_signals(URL, page(body="<p>Mutual funds and insurance</p>")) == []
    assert detect_signals(URL, "") == []


def test_repeated_identical_text_is_stored_once_and_results_are_capped():
    repeated = "<h2>NRI services</h2>" * 3
    many = "".join(f"<h2>NRI offer number {i}</h2>" for i in range(30))

    assert len(detect_signals(URL, page(body=repeated))) == 1
    assert len(detect_signals(URL, page(body=many))) == 10


def test_high_signals_sort_before_low():
    body = "<h2>NRI services</h2><p>We know FEMA.</p>"

    signals = detect_signals(URL, page(body=body))

    assert [s.confidence for s in signals][0] == Confidence.HIGH
    assert signals[-1].confidence == Confidence.LOW


@pytest.mark.parametrize(
    "email,domain",
    [("A@Firm.COM", "firm.com"), ("x@www.firm.com", "firm.com"), ("bad", None), ("a@b@c.com", None), (None, None)],
)
def test_domain_from_email(email, domain):
    assert domain_from_email(email) == domain


@pytest.mark.parametrize(
    "domain,expected",
    [
        ("sampleadvisers.com", True),
        ("gmail.com", False),
        ("yahoo.co.in", False),
        ("localhost", False),
        ("intranet.local", False),
        ("10.0.0.1", False),
        ("nodot", False),
        ("-bad-.com", False),
    ],
)
def test_public_firm_domain(domain, expected):
    assert is_public_firm_domain(domain) is expected


def test_candidate_domains_skip_generic_and_widely_shared_domains():
    emails = {
        "p1": ["a@gmail.com", "b@ownfirm.in"],
        "p2": ["a@bigbank.com"],
        "p3": ["b@bigbank.com"],
        "p4": ["c@bigbank.com"],
        "p5": ["d@bigbank.com"],
        "p6": ["x@yahoo.com"],
    }

    assert candidate_domains(emails, shared_domain_limit=3) == {"p1": {"ownfirm.in"}}


def test_short_link_label_does_not_swallow_body_mentions():
    body = '<nav><a href="/x">NRI</a></nav><p>' + "Filler text. " * 10 + "NRI clients welcome here." + "</p>"

    locations = {s.location for s in detect_signals(URL, page(body=body))}

    assert locations == {Location.LINK, Location.BODY}
