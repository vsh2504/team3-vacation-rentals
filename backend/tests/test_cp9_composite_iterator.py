"""CP9 - Composite (completeness tree) and Iterator (walking handler chains)."""
from datetime import time

from app.domain import Listing, ListingStatus
from app.services.availability import (ApprovalCheck, GuestCountCheck, OperatingHoursCheck,
                                       OverlapCheck, StayRulesCheck, build_availability_chain)
from app.services.chain import ChainLink
from app.services.completeness import (COMPLETENESS_TREE, CheckGroup, FieldCheck,
                                       listing_completeness)
from app.services.listing_validation import (NormalizeText, RequiredText, build_chain,
                                             default_rules)


def listing(**kw):
    base = dict(id=1, host_id=1, title="T", description="d", address="a", city="c",
                state="s", zip="95110", lat=1.0, lng=1.0, price_per_night=100,
                max_guests=2, bedrooms=1, bathrooms=1, amenities=["wifi"],
                host_contact_email="h@x.io", photos=["p.jpg"],
                operating_start_time=time(8, 0), operating_end_time=time(20, 0),
                status=ListingStatus.APPROVED)
    base.update(kw)
    return Listing(**base)


# ---- Composite ----------------------------------------------------------------
def test_leaf_and_group_share_the_evaluate_interface():
    leaf = FieldCheck("title", lambda l: bool(l.title))
    group = CheckGroup("g", [leaf, CheckGroup("inner", [FieldCheck("city", lambda l: bool(l.city))])])
    assert leaf.evaluate(listing()) == {"title": True}
    assert group.evaluate(listing()) == {"title": True, "city": True}


def test_group_iterates_its_leaves_depth_first():
    group = CheckGroup("g", [FieldCheck("a", bool), CheckGroup("n", [FieldCheck("b", bool)]),
                             FieldCheck("c", bool)])
    assert [leaf.name for leaf in group] == ["a", "b", "c"]


def test_tree_covers_the_same_fourteen_checks_in_order():
    assert [leaf.name for leaf in COMPLETENESS_TREE] == [
        "title", "description", "address", "city", "state", "zip", "coordinates",
        "price_per_night", "max_guests", "amenities", "available_times",
        "operating_hours", "contact", "media"]


def test_complete_listing_scores_100_and_incomplete_reports_missing():
    assert listing_completeness(listing())["score"] == 100
    report = listing_completeness(listing(photos=[], amenities=[]))
    assert report["missing"] == ["amenities", "media"] and report["score"] == 86


# ---- Iterator ------------------------------------------------------------------
def test_availability_chain_is_iterable_in_order():
    assert [type(c) for c in build_availability_chain()] == [
        GuestCountCheck, StayRulesCheck, ApprovalCheck, OperatingHoursCheck, OverlapCheck]


def test_validation_chain_is_iterable_and_independent_per_build():
    first, second = build_chain(default_rules()), build_chain(default_rules())
    assert [type(r) for r in first][:2] == [NormalizeText, RequiredText]
    assert len(list(first)) == len(list(second)) == 12


def test_iteration_can_be_repeated_and_single_link_yields_itself():
    link = ChainLink()
    assert list(link) == [link] and list(link) == [link]
    tail = ChainLink()
    link.then(tail)
    assert list(link) == [link, tail]
