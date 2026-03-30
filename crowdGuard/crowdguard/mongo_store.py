from __future__ import annotations

import os
import smtplib
from datetime import UTC, datetime
from email.message import EmailMessage
from typing import Any

import bcrypt
from pymongo import ASCENDING, DESCENDING, MongoClient, ReturnDocument
from pymongo.collection import Collection
from pymongo.errors import DuplicateKeyError


class MongoStore:
    def __init__(self) -> None:
        self.mongo_uri = os.getenv("MONGODB_URI", "mongodb://127.0.0.1:27017")
        self.default_admin_email = os.getenv("DEFAULT_ADMIN_EMAIL", "2306252@kiit.ac.in").strip().lower()
        self.default_admin_password = os.getenv("DEFAULT_ADMIN_PASSWORD", "Admin@12345")
        self.smtp_host = os.getenv("SMTP_HOST", "").strip()
        self.smtp_port = int(os.getenv("SMTP_PORT", "587") or 587)
        self.smtp_username = os.getenv("SMTP_USERNAME", "").strip()
        self.smtp_password = os.getenv("SMTP_PASSWORD", "").strip()
        self.smtp_sender = os.getenv("SMTP_SENDER", self.default_admin_email).strip()

        self.client = MongoClient(self.mongo_uri, serverSelectionTimeoutMS=4000)
        self.admin_db = self.client["crowdguard_admin"]
        self.viewer_db = self.client["crowdguard_viewers"]
        self.logs_db = self.client["crowdguard_logs"]

        self.admin_users = self.admin_db["admin_users"]
        self.viewer_users = self.viewer_db["viewer_users"]
        self.alert_logs = self.logs_db["alert_logs"]
        self.metric_snapshots = self.logs_db["metric_snapshots"]
        self.error_logs = self.logs_db["error_logs"]
        self.password_reset_requests = self.logs_db["password_reset_requests"]
        self.activity_logs = self.logs_db["activity_logs"]

        self._ensure_indexes()
        self._ensure_default_admin()

    def _ensure_indexes(self) -> None:
        self.admin_users.create_index([("email", ASCENDING)], unique=True)
        self.viewer_users.create_index([("email", ASCENDING)], unique=True)
        self.alert_logs.create_index([("created_at", DESCENDING)])
        self.metric_snapshots.create_index([("created_at", DESCENDING)])
        self.error_logs.create_index([("created_at", DESCENDING)])
        self.password_reset_requests.create_index([("created_at", DESCENDING)])
        self.activity_logs.create_index([("created_at", DESCENDING)])

    def _ensure_default_admin(self) -> None:
        defaults = [
            {
                "collection": self.admin_users,
                "name": "Default CrowdGuard Admin",
                "email": self.default_admin_email,
                "password": self.default_admin_password,
                "role": "admin",
            },
            {
                "collection": self.admin_users,
                "name": "Demo Admin",
                "email": "admin@ex.gmail.com",
                "password": "admin12@3",
                "role": "admin",
            },
            {
                "collection": self.viewer_users,
                "name": "Demo Viewer",
                "email": "user@ex.gmail.com",
                "password": "user@123",
                "role": "viewer",
            },
        ]

        for item in defaults:
            if item["collection"].find_one({"email": item["email"]}):
                continue
            item["collection"].insert_one(
                {
                    "name": item["name"],
                    "email": item["email"],
                    "password_hash": self._hash_password(item["password"]),
                    "role": item["role"],
                    "approved": True,
                    "created_at": self._utc_now(),
                    "updated_at": self._utc_now(),
                }
            )

    @staticmethod
    def _utc_now() -> datetime:
        return datetime.now(UTC)

    @staticmethod
    def _hash_password(password: str) -> str:
        return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

    @staticmethod
    def _verify_password(password: str, password_hash: str) -> bool:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))

    @staticmethod
    def _serialize_doc(document: dict[str, Any] | None) -> dict[str, Any] | None:
        if document is None:
            return None
        payload = dict(document)
        if "_id" in payload:
            payload["_id"] = str(payload["_id"])
        for key, value in list(payload.items()):
            if isinstance(value, datetime):
                payload[key] = value.isoformat()
        return payload

    @staticmethod
    def _serialize_many(cursor) -> list[dict[str, Any]]:
        items: list[dict[str, Any]] = []
        for document in cursor:
            payload = MongoStore._serialize_doc(document)
            if payload is not None:
                items.append(payload)
        return items

    def _collection_for_role(self, role: str) -> Collection:
        return self.admin_users if role == "admin" else self.viewer_users

    def request_viewer_access(self, name: str, email: str, password: str) -> dict[str, Any]:
        email = email.strip().lower()
        name = name.strip()

        if not name or not email or not password:
            raise ValueError("Name, email, and password are required.")

        payload = {
            "name": name,
            "email": email,
            "password_hash": self._hash_password(password),
            "role": "viewer",
            "approved": False,
            "approved_by": None,
            "created_at": self._utc_now(),
            "updated_at": self._utc_now(),
        }
        try:
            self.viewer_users.insert_one(payload)
        except DuplicateKeyError:
            existing = self.viewer_users.find_one({"email": email})
            if existing and existing.get("approved"):
                raise ValueError("That viewer account already exists.")
            raise ValueError("An access request for that email already exists.")

        self.activity_logs.insert_one(
            {
                "type": "signup_request",
                "email": email,
                "message": f"Viewer access request submitted for approval by {self.default_admin_email}.",
                "created_at": self._utc_now(),
            }
        )
        self._send_email_notice(
            subject="CrowdGuard viewer access request",
            body=f"{name} ({email}) requested viewer access to CrowdGuard.",
        )
        return {"status": "pending", "message": f"Approval request sent to {self.default_admin_email}."}

    def create_user(self, name: str, email: str, password: str, role: str) -> dict[str, Any]:
        role = (role or "viewer").strip().lower()
        email = email.strip().lower()
        name = name.strip()

        if role not in {"viewer", "admin"}:
            raise ValueError("Role must be viewer or admin.")
        if not name or not email or not password:
            raise ValueError("Name, email, and password are required.")

        collection = self._collection_for_role(role)
        payload = {
            "name": name,
            "email": email,
            "password_hash": self._hash_password(password),
            "role": role,
            "approved": True,
            "approved_by": self.default_admin_email if role == "viewer" else None,
            "created_at": self._utc_now(),
            "updated_at": self._utc_now(),
        }
        try:
            collection.insert_one(payload)
        except DuplicateKeyError:
            raise ValueError(f"An account with that {role} email already exists.")

        self.activity_logs.insert_one(
            {
                "type": "signup",
                "role": role,
                "email": email,
                "message": f"{role.title()} account created.",
                "created_at": self._utc_now(),
            }
        )
        return {
            "status": "created",
            "user": {
                "name": name,
                "email": email,
                "role": role,
                "approved": True,
            },
        }

    def login(self, email: str, password: str) -> dict[str, Any]:
        email = email.strip().lower()
        if not email or not password:
            raise ValueError("Email and password are required.")

        admin = self.admin_users.find_one({"email": email})
        if admin and self._verify_password(password, admin["password_hash"]):
            return {
                "name": admin.get("name", "Admin"),
                "email": email,
                "role": "admin",
                "approved": True,
            }

        viewer = self.viewer_users.find_one({"email": email})
        if viewer is None:
            raise ValueError("No account found for that email.")
        if not viewer.get("approved"):
            raise ValueError(f"This account is waiting for approval from {self.default_admin_email}.")
        if not self._verify_password(password, viewer["password_hash"]):
            raise ValueError("Invalid password.")
        return {
            "name": viewer.get("name", "Viewer"),
            "email": email,
            "role": "viewer",
            "approved": True,
        }

    def request_password_reset(self, email: str) -> dict[str, Any]:
        email = email.strip().lower()
        if not email:
            raise ValueError("Email is required.")

        message = f"Password reset request raised for {email}. Notify {self.default_admin_email}."
        self.password_reset_requests.insert_one(
            {
                "email": email,
                "message": message,
                "created_at": self._utc_now(),
                "status": "pending",
            }
        )
        self._send_email_notice(
            subject="CrowdGuard password reset request",
            body=f"A password reset was requested for {email}. Please review it from the admin account {self.default_admin_email}.",
        )
        return {"status": "queued", "message": f"Password reset request sent to {self.default_admin_email}."}

    def approve_viewer(self, email: str, admin_email: str) -> dict[str, Any]:
        email = email.strip().lower()
        admin_email = admin_email.strip().lower()
        admin = self.admin_users.find_one({"email": admin_email})
        if admin is None:
            raise ValueError("Admin account not found.")

        updated = self.viewer_users.find_one_and_update(
            {"email": email},
            {"$set": {"approved": True, "approved_by": admin_email, "updated_at": self._utc_now()}},
            return_document=ReturnDocument.AFTER,
        )
        if updated is None:
            raise ValueError("Viewer account not found.")

        self.activity_logs.insert_one(
            {
                "type": "approval",
                "email": email,
                "approved_by": admin_email,
                "message": f"Viewer account approved by {admin_email}.",
                "created_at": self._utc_now(),
            }
        )
        return {"status": "approved", "email": email}

    def get_pending_viewers(self) -> list[dict[str, Any]]:
        cursor = self.viewer_users.find({"approved": False}).sort("created_at", DESCENDING)
        return self._serialize_many(cursor)

    def log_alert(self, severity: str, payload: dict[str, Any]) -> None:
        self.alert_logs.insert_one(
            {
                **payload,
                "severity": severity,
                "created_at": self._utc_now(),
            }
        )

    def log_metric_snapshot(self, payload: dict[str, Any]) -> None:
        self.metric_snapshots.insert_one({**payload, "created_at": self._utc_now()})

    def log_error(self, payload: dict[str, Any]) -> None:
        self.error_logs.insert_one({**payload, "created_at": self._utc_now()})

    def get_logs(self, collection: str, limit: int = 50) -> list[dict[str, Any]]:
        mapping = {
            "alerts": self.alert_logs,
            "metrics": self.metric_snapshots,
            "errors": self.error_logs,
            "password_resets": self.password_reset_requests,
            "activity": self.activity_logs,
        }
        target = mapping[collection]
        return self._serialize_many(target.find().sort("created_at", DESCENDING).limit(limit))

    def _send_email_notice(self, subject: str, body: str) -> bool:
        if not self.smtp_host or not self.smtp_username or not self.smtp_password:
            return False

        message = EmailMessage()
        message["From"] = self.smtp_sender
        message["To"] = self.default_admin_email
        message["Subject"] = subject
        message.set_content(body)

        with smtplib.SMTP(self.smtp_host, self.smtp_port, timeout=10) as smtp:
            smtp.starttls()
            smtp.login(self.smtp_username, self.smtp_password)
            smtp.send_message(message)
        return True
