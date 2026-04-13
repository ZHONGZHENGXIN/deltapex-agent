from typing import Annotated

import redis
from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlmodel import Session

from app.core.i18n import Language
from app.db.base import get_session
from app.models.user import User
from app.services.supabase_auth import sync_local_user_from_supabase, verify_supabase_access_token


def get_redis(request: Request):
    return request.app.state.redis


RedisDep = Annotated[redis.Redis, Depends(get_redis)]
SessionDep = Annotated[Session, Depends(get_session)]

scheme = HTTPBearer()


def get_user(credentials: HTTPAuthorizationCredentials = Depends(scheme), session: Session = Depends(get_session)) -> User:
    try:
        claims = verify_supabase_access_token(credentials.credentials)
        return sync_local_user_from_supabase(session, claims)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=401, detail="Invalid access token") from exc


def get_language(request: Request) -> str:
    accept_language = request.headers.get("Accept-Language", "")
    if accept_language:
        languages = []
        for lang_item in accept_language.split(","):
            lang_code = lang_item.split(";")[0].strip().lower()
            primary_lang = lang_code.split("-")[0]
            if primary_lang in [Language.ZH.value, Language.EN.value]:
                languages.append(primary_lang)

        if languages:
            return languages[0]

    return Language.ZH.value


UserDep = Annotated[User, Depends(get_user)]
LangDep = Annotated[str, Depends(get_language)]
