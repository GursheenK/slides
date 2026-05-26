"""Reconcile users needed by migrated Drive/Slides/Writer data.

This is intentionally separate from the data/file merge:
- dry-run reports missing users, missing Drive User roles, and missing Drive Settings
- apply creates missing users as enabled Website Users
- apply adds Drive User and creates Drive Settings idempotently
- existing User fields are never overwritten
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any


def find_bench_path() -> Path:
	cwd = Path.cwd().resolve()
	if (cwd / "sites").exists() and (cwd / "apps").exists():
		return cwd

	for parent in Path(__file__).resolve().parents:
		if (parent / "sites").exists() and (parent / "apps").exists():
			return parent

	raise RuntimeError("Could not find bench root containing both sites/ and apps/")


BENCH_PATH = find_bench_path()
SITES_PATH = BENCH_PATH / "sites"
os.chdir(SITES_PATH)

for app_path in (BENCH_PATH / "apps").iterdir():
	if app_path.is_dir():
		sys.path.insert(0, str(app_path))

import frappe  # noqa: E402
from frappe.utils import cint, cstr, validate_email_address  # noqa: E402

REFERENCE_FIELDS = {
	"Drive File": ("owner", "modified_by"),
	"Drive Permission": ("owner", "modified_by", "user"),
	"Drive Team": ("owner", "modified_by"),
	"Drive Team Member": ("owner", "modified_by", "user"),
	"Drive Document": ("owner", "modified_by"),
	"Drive Document Version": ("owner", "modified_by"),
	"Drive Favourite": ("owner", "modified_by", "user"),
	"Drive Notification": ("owner", "modified_by", "to_user", "from_user"),
	"Drive Settings": ("owner", "modified_by", "user"),
	"Writer Document": ("owner", "modified_by"),
	"Writer Version": ("owner", "modified_by"),
	"Writer Template": ("owner", "modified_by"),
	"Presentation": ("owner", "modified_by"),
	"File": ("owner", "modified_by"),
}

IGNORED_USERS = {"", "Administrator", "Guest"}


def execute(
	source_site: str,
	target_site: str,
	dry_run: int = 1,
	create_drive_settings: int = 1,
) -> dict[str, Any]:
	"""Create/repair Suite users required by migrated Drive data.

	Args:
		source_site: Source site containing Drive/Slides/Writer data.
		target_site: Suite target site where users should exist.
		dry_run: 1 reports only. 0 applies idempotent fixes.
	"""
	dry_run = cint(dry_run)

	source_users = get_referenced_users_with_source_info(source_site)
	create_drive_settings = cint(create_drive_settings)
	report = inspect_target(target_site, source_users, create_drive_settings=create_drive_settings)
	print_report(source_site, target_site, report, dry_run)

	if dry_run:
		return summarize_report(report) | {"status": "dry_run"}

	apply_target_fixes(target_site, report)
	return summarize_report(report) | {"status": "applied"}


def get_referenced_users_with_source_info(site: str) -> dict[str, dict[str, Any]]:
	connect(site)
	try:
		users = collect_referenced_users()
		user_info = {}
		for user in users:
			info = frappe.db.get_value(
				"User",
				user,
				[
					"email",
					"first_name",
					"last_name",
					"full_name",
					"user_image",
					"language",
					"time_zone",
					"enabled",
				],
				as_dict=True,
			)
			user_info[user] = dict(info or {})
		return user_info
	finally:
		disconnect()


def collect_referenced_users() -> set[str]:
	users = set()
	for doctype, fields in REFERENCE_FIELDS.items():
		if not frappe.db.exists("DocType", doctype):
			continue

		valid_fields = [field for field in fields if frappe.db.has_column(doctype, field)]
		if not valid_fields:
			continue

		for field in valid_fields:
			values = frappe.get_all(doctype, pluck=field)
			for value in values:
				normalized = normalize_user(value)
				if normalized:
					users.add(normalized)

	return users


def inspect_target(
	target_site: str,
	source_users: dict[str, dict[str, Any]],
	create_drive_settings: int = 1,
) -> dict[str, Any]:
	connect(target_site)
	try:
		missing_users = []
		invalid_users = []
		disabled_users = []
		missing_drive_user_role = []
		missing_drive_settings = []
		existing_users = []

		for user, source_info in sorted(source_users.items()):
			if not is_valid_email_user(user):
				invalid_users.append(user)
				continue
			if is_disabled_source_user(source_info):
				disabled_users.append(user)
				continue

			if not frappe.db.exists("User", user):
				missing_users.append({"user": user, "source_info": source_info})
				missing_drive_user_role.append(user)
				if create_drive_settings:
					missing_drive_settings.append(user)
				continue

			existing_users.append(user)
			if not has_role(user, "Drive User"):
				missing_drive_user_role.append(user)
			if create_drive_settings and not frappe.db.exists("Drive Settings", user):
				missing_drive_settings.append(user)

		return {
			"referenced_users": sorted(source_users),
			"invalid_users": invalid_users,
			"disabled_users": disabled_users,
			"missing_users": missing_users,
			"existing_users": existing_users,
			"missing_drive_user_role": sorted(set(missing_drive_user_role)),
			"missing_drive_settings": sorted(set(missing_drive_settings)),
		}
	finally:
		disconnect()


def apply_target_fixes(target_site: str, report: dict[str, Any]) -> None:
	connect(target_site)
	try:
		created_users = 0
		added_roles = 0
		created_settings = 0

		for row in report["missing_users"]:
			user = row["user"]
			if frappe.db.exists("User", user):
				continue
			create_website_user_from_import(user, row.get("source_info") or {})
			created_users += 1

		for user in report["missing_drive_user_role"]:
			if not frappe.db.exists("User", user):
				print(f"Skipping Drive User role for missing user: {user}")
				continue
			if has_role(user, "Drive User"):
				continue
			insert_user_role(user, "Drive User")
			added_roles += 1

		for user in report["missing_drive_settings"]:
			if not frappe.db.exists("User", user):
				print(f"Skipping Drive Settings for missing user: {user}")
				continue
			if frappe.db.exists("Drive Settings", user):
				continue
			insert_drive_settings(user)
			created_settings += 1

		frappe.db.commit()
		clear_user_caches()
		print(f"Created users: {created_users}")
		print(f"Added Drive User roles: {added_roles}")
		print(f"Created Drive Settings: {created_settings}")
	finally:
		disconnect()


def create_website_user_from_import(user: str, source_info: dict[str, Any]) -> None:
	previous_in_import = getattr(frappe.flags, "in_import", None)
	frappe.flags.in_import = True
	try:
		create_website_user(user, source_info)
	finally:
		if previous_in_import is None:
			frappe.flags.pop("in_import", None)
		else:
			frappe.flags.in_import = previous_in_import


def create_website_user(user: str, source_info: dict[str, Any]) -> None:
	first_name = cstr(source_info.get("first_name")).strip() or derive_first_name(user)
	last_name = cstr(source_info.get("last_name")).strip()

	doc = frappe.get_doc(
		{
			"doctype": "User",
			"email": user,
			"first_name": first_name,
			"last_name": last_name,
			"enabled": 1,
			"user_type": "Website User",
			"send_welcome_email": 0,
			"user_image": source_info.get("user_image"),
			"language": source_info.get("language"),
			"time_zone": source_info.get("time_zone"),
		}
	)
	doc.name = user
	doc.db_insert()


def insert_user_role(user: str, role: str) -> None:
	frappe.get_doc(
		{
			"doctype": "Has Role",
			"name": frappe.generate_hash(length=10),
			"parent": user,
			"parenttype": "User",
			"parentfield": "roles",
			"role": role,
		}
	).db_insert()


def insert_drive_settings(user: str) -> None:
	frappe.get_doc({"doctype": "Drive Settings", "name": user, "user": user}).db_insert()


def clear_user_caches() -> None:
	frappe.cache.delete_key("users_for_mentions")
	frappe.cache.delete_key("enabled_users")
	frappe.clear_cache(doctype="User")


def has_role(user: str, role: str) -> bool:
	return bool(frappe.db.exists("Has Role", {"parent": user, "role": role}))


def print_report(source_site: str, target_site: str, report: dict[str, Any], dry_run: int) -> None:
	print(f"Source: {source_site}")
	print(f"Target: {target_site}")
	print(f"Mode: {'dry-run' if dry_run else 'apply'}")
	print(f"Referenced users: {len(report['referenced_users'])}")
	print(f"Invalid/skipped users: {len(report['invalid_users'])}")
	print(f"Disabled/skipped users: {len(report['disabled_users'])}")
	print(f"Missing User records: {len(report['missing_users'])}")
	print(f"Existing User records: {len(report['existing_users'])}")
	print(f"Missing Drive User roles: {len(report['missing_drive_user_role'])}")
	print(f"Missing Drive Settings: {len(report['missing_drive_settings'])}")

	for title, values in (
		("Invalid/skipped users", report["invalid_users"]),
		("Disabled/skipped users", report["disabled_users"]),
		("Missing User records", [row["user"] for row in report["missing_users"]]),
		("Missing Drive User roles", report["missing_drive_user_role"]),
		("Missing Drive Settings", report["missing_drive_settings"]),
	):
		if values:
			print(title + ":")
			for value in values[:50]:
				print(f"  - {value}")
			if len(values) > 50:
				print(f"  ... {len(values) - 50} more")


def summarize_report(report: dict[str, Any]) -> dict[str, int]:
	return {
		"referenced_users": len(report["referenced_users"]),
		"invalid_users": len(report["invalid_users"]),
		"disabled_users": len(report["disabled_users"]),
		"missing_users": len(report["missing_users"]),
		"existing_users": len(report["existing_users"]),
		"missing_drive_user_role": len(report["missing_drive_user_role"]),
		"missing_drive_settings": len(report["missing_drive_settings"]),
	}


def normalize_user(value) -> str | None:
	value = cstr(value).strip()
	if value in IGNORED_USERS:
		return None
	return value


def is_valid_email_user(user: str) -> bool:
	try:
		return bool(validate_email_address(user, throw=False))
	except Exception:
		return False


def is_disabled_source_user(source_info: dict[str, Any]) -> bool:
	return "enabled" in source_info and not cint(source_info.get("enabled"))


def derive_first_name(user: str) -> str:
	local_part = user.split("@", 1)[0]
	return local_part.replace(".", " ").replace("_", " ").replace("-", " ").title() or user


def connect(site: str) -> None:
	disconnect()
	frappe.init(site=site, sites_path=str(SITES_PATH))
	frappe.connect()


def disconnect() -> None:
	try:
		if getattr(frappe.local, "db", None):
			frappe.db.close()
	except Exception:
		pass
	try:
		frappe.destroy()
	except Exception:
		pass
