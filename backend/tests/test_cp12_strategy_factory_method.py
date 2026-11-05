"""CP12 - Strategy (hashing, tokens, navigation, upload signatures, stay rules),
Factory Method (ApiError), Composite (router registry), Facade (core, app root)."""
import pytest
from fastapi import FastAPI

import app as app_pkg
from app import core
from app.core import security
from app.core.errors import ApiError
from app.core.security import (HmacTokenCodec, Pbkdf2Hasher, check_password, decode_token,
                               hash_password, make_token)
from app.domain import UserRole
from app.routers import ROUTERS, include_all, uploads
from app.services.navigation import NAVIGATION_STRATEGIES, navigation_for
from app.services.stay_window import (DurationRule, PairRule, RangeRule, StayDraft, TimesRule,
                                      resolve_stay_window)
from datetime import date, time


# ---- Factory Method -----------------------------------------------------------------
@pytest.mark.parametrize("factory,code,status", [
    (ApiError.validation, "VALIDATION_ERROR", 422), (ApiError.unauthorized, "UNAUTHORIZED", 401),
    (ApiError.forbidden, "FORBIDDEN", 403), (ApiError.not_found, "NOT_FOUND", 404),
    (ApiError.conflict, "CONFLICT", 409)])
def test_api_error_factory_methods(factory, code, status):
    err = factory("boom")
    assert (err.code, err.message, err.status) == (code, "boom", status)


def test_validation_factory_carries_the_field():
    assert ApiError.validation("bad", "email").envelope()["error"]["field"] == "email"


# ---- Strategy: password hashing + tokens ----------------------------------------------
def test_pbkdf2_hasher_strategy_matches_module_functions():
    hasher = Pbkdf2Hasher(iterations=1000)
    stored = hasher.hash("secret-pass", salt="s")
    assert stored.startswith("pbkdf2:s:") and hasher.verify("secret-pass", stored)
    assert not hasher.verify("other", stored) and not hasher.verify("x", "garbage")
    assert check_password("pw-12345", hash_password("pw-12345"))


def test_token_codec_strategy_round_trip_and_rejections():
    codec = HmacTokenCodec(secret="k")
    token = codec.encode(5, "HOST", ttl_seconds=60)
    assert codec.decode(token)["sub"] == 5 and decode_token(make_token(3, "ADMIN"))["role"] == "ADMIN"
    with pytest.raises(ValueError):
        HmacTokenCodec(secret="other").decode(token)
    with pytest.raises(ValueError):
        codec.decode(codec.encode(5, "HOST", ttl_seconds=-5))
    assert security.DEFAULT_HASHER and security.DEFAULT_CODEC


# ---- Strategy: navigation ---------------------------------------------------------------
def test_each_role_has_a_navigation_strategy_returning_fresh_copies():
    assert set(NAVIGATION_STRATEGIES) == set(UserRole)
    first = navigation_for("HOST")
    first[0]["label"] = "mutated"
    assert navigation_for(UserRole.HOST)[0]["label"] == "Search stays"
    assert [i["key"] for i in navigation_for(UserRole.ADMIN)] == ["search", "moderation", "analytics"]


# ---- Strategy: upload signatures ---------------------------------------------------------
@pytest.mark.parametrize("ctype,data,ok", [
    ("image/jpeg", b"\xff\xd8\xff\xe0", True), ("image/jpeg", b"nope", False),
    ("image/png", b"\x89PNG\r\n\x1a\n", True), ("image/gif", b"GIF89a..", True),
    ("image/webp", b"RIFF\0\0\0\0WEBP", True), ("video/mp4", b"\0\0\0\x18ftyp", True),
    ("video/webm", b"\x1a\x45\xdf\xa3", True), ("text/plain", b"hello", False)])
def test_signature_strategies(ctype, data, ok):
    assert uploads._matches_signature(ctype, data) is ok


# ---- Chain: stay window rules -------------------------------------------------------------
def test_stay_window_rules_run_in_a_chain():
    draft = StayDraft(date(2027, 5, 1), None, 3, None, None)
    for rule in (DurationRule(), PairRule(), RangeRule(), TimesRule()):
        rule.apply(draft)
    assert draft.check_out == date(2027, 5, 4) and draft.stay_nights == 3
    window = resolve_stay_window(date(2027, 5, 1), date(2027, 5, 3), None, time(9), time(10))
    assert window.nights == 2


# ---- Composite + Facades ---------------------------------------------------------------------
def test_router_registry_mounts_every_router_once():
    app = FastAPI()
    include_all(app)
    paths = set(app.openapi()["paths"])
    assert len(ROUTERS) == 7 and "/auth/login" in paths and "/uploads" in paths


def test_core_and_app_root_are_facades():
    assert core.ApiError is ApiError and core.ok({"a": 1})["success"] is True
    assert core.hash_password is hash_password and core.decode_token is decode_token
    assert callable(app_pkg.create_app)
    with pytest.raises(AttributeError):
        app_pkg.does_not_exist


def test_create_app_is_a_factory_method_producing_independent_apps():
    first, second = app_pkg.create_app(), app_pkg.create_app()
    assert first is not second and isinstance(first, FastAPI)
