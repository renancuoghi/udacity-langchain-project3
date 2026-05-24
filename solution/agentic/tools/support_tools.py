from __future__ import annotations

from typing import Any

from sqlalchemy.orm import joinedload

from solution.data.models import cultpass
from solution.db import EXTERNAL_DB_PATH, session_scope, sqlite_engine


class SupportTools:
    def __init__(self) -> None:
        self.external_engine = sqlite_engine(EXTERNAL_DB_PATH)

    def account_lookup(self, external_user_id: str) -> dict[str, Any]:
        with session_scope(self.external_engine) as session:
            user = (
                session.query(cultpass.User)
                .options(joinedload(cultpass.User.subscription))
                .filter(cultpass.User.user_id == external_user_id)
                .one_or_none()
            )
            if not user:
                return {"ok": False, "error": "user_not_found", "external_user_id": external_user_id}

            subscription = user.subscription
            return {
                "ok": True,
                "user": {
                    "user_id": user.user_id,
                    "full_name": user.full_name,
                    "email": user.email,
                    "is_blocked": user.is_blocked,
                },
                "subscription": {
                    "status": subscription.status if subscription else None,
                    "tier": subscription.tier if subscription else None,
                    "monthly_quota": subscription.monthly_quota if subscription else None,
                },
            }

    def get_recent_reservations(self, external_user_id: str, limit: int = 3) -> dict[str, Any]:
        with session_scope(self.external_engine) as session:
            user = session.query(cultpass.User).filter(cultpass.User.user_id == external_user_id).one_or_none()
            if not user:
                return {"ok": False, "error": "user_not_found", "external_user_id": external_user_id}

            reservations = (
                session.query(cultpass.Reservation)
                .options(joinedload(cultpass.Reservation.experience))
                .filter(cultpass.Reservation.user_id == external_user_id)
                .order_by(cultpass.Reservation.created_at.desc())
                .limit(limit)
                .all()
            )
            return {
                "ok": True,
                "reservations": [
                    {
                        "reservation_id": row.reservation_id,
                        "status": row.status,
                        "experience_title": row.experience.title,
                        "experience_location": row.experience.location,
                    }
                    for row in reservations
                ],
            }

    def set_subscription_status(self, external_user_id: str, new_status: str) -> dict[str, Any]:
        allowed = {"active", "paused", "canceled", "suspended"}
        if new_status not in allowed:
            return {
                "ok": False,
                "error": "invalid_status",
                "allowed_status": sorted(allowed),
                "requested_status": new_status,
            }

        with session_scope(self.external_engine) as session:
            subscription = (
                session.query(cultpass.Subscription)
                .filter(cultpass.Subscription.user_id == external_user_id)
                .one_or_none()
            )
            if not subscription:
                return {"ok": False, "error": "subscription_not_found", "external_user_id": external_user_id}

            subscription.status = new_status
            return {
                "ok": True,
                "subscription": {
                    "user_id": external_user_id,
                    "status": subscription.status,
                    "tier": subscription.tier,
                    "monthly_quota": subscription.monthly_quota,
                },
            }
