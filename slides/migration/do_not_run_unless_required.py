"""Remove target Drive Settings rows that should be imported from a source site."""

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
from frappe.utils import cint  # noqa: E402


def execute(source_site: str, target_site: str, dry_run: int = 1) -> dict[str, Any]:
	"""Delete target Drive Settings docs whose names exist in the source site.

	This is for the Drive-to-Suite merge when target rows were generated before
	the merge. Source Drive Settings should be imported as the source of truth.
	"""
	dry_run = cint(dry_run)
	source_names = get_drive_settings_names(source_site)
	target_names = get_existing_target_names(target_site, source_names)

	print(f"Source: {source_site}")
	print(f"Target: {target_site}")
	print(f"Mode: {'dry-run' if dry_run else 'apply'}")
	print(f"Source Drive Settings: {len(source_names)}")
	print(f"Target conflicts to remove: {len(target_names)}")
	for name in target_names[:50]:
		print(f"  - {name}")
	if len(target_names) > 50:
		print(f"  ... {len(target_names) - 50} more")

	if dry_run:
		return {
			"source_drive_settings": len(source_names),
			"target_conflicts": len(target_names),
			"status": "dry_run",
		}

	connect(target_site)
	try:
		for name in target_names:
			frappe.db.delete("Drive Settings", {"name": name})
		frappe.db.commit()
	finally:
		disconnect()

	return {"source_drive_settings": len(source_names), "removed": len(target_names), "status": "applied"}


def get_drive_settings_names(site: str) -> set[str]:
	connect(site)
	try:
		if not frappe.db.exists("DocType", "Drive Settings"):
			return set()
		return set(frappe.get_all("Drive Settings", pluck="name"))
	finally:
		disconnect()


def get_existing_target_names(site: str, names: set[str]) -> list[str]:
	if not names:
		return []

	connect(site)
	try:
		if not frappe.db.exists("DocType", "Drive Settings"):
			return []

		existing = []
		for name in sorted(names):
			if frappe.db.exists("Drive Settings", name):
				existing.append(name)
		return existing
	finally:
		disconnect()


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
