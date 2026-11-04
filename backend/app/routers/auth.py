"""Core API — Ranadhir Reddy Rikkala
Feature: Identity, Platform & Admin Control (auth half)
Endpoints:
  POST /auth/register   (role CUSTOMER|HOST only; Admin is seeded)
  POST /auth/login      (returns JWT with sub, role, exp)
  GET  /auth/me         (Bearer token -> current user)
File owner in CODEOWNERS / docs: Ranadhir Reddy Rikkala.
Admin moderation endpoints live in admin.py — same owner, same core API."""
from fastapi import APIRouter, Depends
from ..core.errors import ok
from ..domain import UserRole
from ..schemas import LoginIn, RegisterIn
from ..services import AuthService
from .common import get_current_user, get_store

router = APIRouter(tags=["auth — Ranadhir Reddy Rikkala"])

@router.post("/auth/register")
def register(body: RegisterIn, store=Depends(get_store)):
    try:
        role = UserRole(body.role)
    except ValueError:
        from ..core.errors import ApiError
        raise ApiError("VALIDATION_ERROR", "role must be CUSTOMER or HOST", "role")
    user = AuthService(store).register(body.email, body.password, body.full_name, role)
    return ok({"id": user.id, "email": user.email, "full_name": user.full_name, "role": user.role.value})

@router.post("/auth/login")
def login(body: LoginIn, store=Depends(get_store)):
    return ok(AuthService(store).login(body.email, body.password))

@router.get("/auth/me")
def me(user=Depends(get_current_user)):
    return ok({"id": user.id, "email": user.email, "full_name": user.full_name, "role": user.role.value})
