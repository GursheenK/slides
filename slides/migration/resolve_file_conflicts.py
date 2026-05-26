from __future__ import annotations

import os
from pathlib import Path
from urllib.parse import quote, unquote

import frappe
from frappe.utils import cint, cstr, get_site_path

CONFLICTING_FILE_URLS = [
	"/private/files/image.webp",
	"/private/files/pasted-image.svg",
	"/private/files/_118283916_b19c5a1f-162b-410b-8169-f58f0d153752.jpg",
]

RESOLVED_SUFFIX = "resolved"
LOCAL_FILE_PREFIXES = ("/files/", "/private/files/")
REFERENCE_TABLES = ("tabPresentation", "tabSlide")


def execute(dry_run=1, file_urls=None, reference_tables=None):
	"""Rename hardcoded conflicting files and update DB references.

	Args:
		dry_run: 1 prints planned changes. 0 applies filesystem and DB changes.
		file_urls: Optional comma-separated/list of file URLs to resolve.
		reference_tables: Optional comma-separated/list of DB tables to scan. Use "*"
			to scan all normal DocType tables.
	"""
	dry_run = cint(dry_run)
	file_urls = normalize_file_url_list(file_urls) or CONFLICTING_FILE_URLS
	reference_tables = normalize_reference_tables(reference_tables)
	planned_urls = get_existing_local_file_urls()
	changes = []
	skipped = []

	for old_url in file_urls:
		old_url = normalize_file_url(old_url)
		file_rows = get_file_rows(old_url)

		if not file_rows:
			skipped.append((old_url, "No File document found for this URL"))
			continue

		new_url = make_resolved_file_url(old_url, planned_urls)
		planned_urls.add(new_url)
		changes.append((old_url, new_url, file_rows))

	print(f"Found {len(changes)} conflicting URL(s) to resolve.")
	for old_url, new_url, file_rows in changes:
		file_names = ", ".join(row.name for row in file_rows)
		print(
			f"{'[dry-run] ' if dry_run else ''}{old_url} -> {new_url} ({len(file_rows)} File doc(s): {file_names})"
		)

	if skipped:
		print("Skipped:")
		for old_url, reason in skipped:
			print(f"- {old_url}: {reason}")

	if dry_run:
		return

	for old_url, new_url, file_rows in changes:
		move_file_on_disk(old_url, new_url)
		update_file_docs(file_rows, new_url)
		replace_file_url_references(old_url, new_url, reference_tables)

	frappe.db.commit()
	print(f"Resolved {len(changes)} conflicting URL(s).")


def get_file_rows(file_url: str):
	alternate_url = alternate_private_public_url(file_url)
	urls = [file_url]
	if alternate_url:
		urls.append(alternate_url)

	return frappe.get_all(
		"File",
		filters={"is_folder": 0, "file_url": ["in", urls]},
		fields=["name", "file_name", "file_url", "is_private"],
		order_by="name",
	)


def get_existing_local_file_urls() -> set[str]:
	return {
		normalize_file_url(url)
		for url in frappe.get_all(
			"File",
			filters={"is_folder": 0, "file_url": ["is", "set"]},
			pluck="file_url",
		)
		if is_local_file_url(url)
	}


def make_resolved_file_url(old_url: str, reserved_urls: set[str]) -> str:
	prefix, encoded_name = old_url.rsplit("/", 1)
	decoded_name = unquote(encoded_name)
	stem, extension = os.path.splitext(decoded_name)

	for index in range(1, 100):
		suffix = RESOLVED_SUFFIX if index == 1 else f"{RESOLVED_SUFFIX}-{index}"
		candidate_name = f"{stem}-{suffix}{extension}"
		candidate_url = f"{prefix}/{quote(candidate_name)}"
		if candidate_url not in reserved_urls and not get_path_from_file_url(candidate_url).exists():
			return candidate_url

	frappe.throw(f"Could not generate a resolved URL for {old_url}")


def move_file_on_disk(old_url: str, new_url: str) -> None:
	old_path = get_path_from_file_url(old_url)
	new_path = get_path_from_file_url(new_url)

	if new_path.exists():
		frappe.throw(f"Target file already exists on disk: {new_path}")

	if not old_path.exists():
		print(f"Warning: source file missing on disk; updating DB only: {old_path}")
		return

	new_path.parent.mkdir(parents=True, exist_ok=True)
	os.rename(old_path, new_path)


def update_file_docs(file_rows, new_url: str) -> None:
	new_file_name = unquote(new_url.rsplit("/", 1)[-1])
	for row in file_rows:
		frappe.db.set_value(
			"File",
			row.name,
			{
				"file_name": new_file_name,
				"file_url": new_url,
				"is_private": 1 if new_url.startswith("/private/files/") else 0,
			},
			update_modified=False,
		)


def replace_file_url_references(old_url: str, new_url: str, reference_tables=None) -> None:
	urls = {old_url}
	alternate_url = alternate_private_public_url(old_url)
	if alternate_url:
		urls.add(alternate_url)

	for table in reference_tables or REFERENCE_TABLES:
		for column in get_text_columns(table):
			for source_url in urls:
				frappe.db.sql(
					f"""
					update `{table}`
					set `{column}` = replace(`{column}`, %s, %s)
					where `{column}` like %s
					""",
					(source_url, new_url, f"%{source_url}%"),
				)


def get_text_columns(table: str) -> list[str]:
	rows = frappe.db.sql(f"show columns from `{table}`", as_dict=True)
	return [row.Field for row in rows if any(kind in row.Type.lower() for kind in ("char", "text", "json"))]


def normalize_file_url_list(file_urls) -> list[str]:
	if not file_urls:
		return []
	if isinstance(file_urls, str):
		return [url.strip() for url in file_urls.split(",") if url.strip()]
	return [url.strip() for url in file_urls if url and url.strip()]


def normalize_reference_tables(reference_tables) -> list[str]:
	if reference_tables == "*":
		return get_all_normal_doctype_tables()
	if not reference_tables:
		return list(REFERENCE_TABLES)
	if isinstance(reference_tables, str):
		return [table.strip() for table in reference_tables.split(",") if table.strip()]
	return [table.strip() for table in reference_tables if table and table.strip()]


def get_all_normal_doctype_tables() -> list[str]:
	tables = []
	for row in frappe.db.sql("show tables", as_list=True):
		table = row[0]
		if table.startswith("tab") and table != "tabSingles":
			tables.append(table)
	return tables


def get_path_from_file_url(file_url: str) -> Path:
	file_name = unquote(file_url.rsplit("/", 1)[-1])
	if file_url.startswith("/private/files/"):
		return Path(get_site_path("private", "files", file_name))
	if file_url.startswith("/files/"):
		return Path(get_site_path("public", "files", file_name))
	frappe.throw(f"Unsupported local file URL: {file_url}")


def alternate_private_public_url(file_url: str) -> str | None:
	if file_url.startswith("/private/files/"):
		return file_url.replace("/private/files/", "/files/", 1)
	if file_url.startswith("/files/"):
		return file_url.replace("/files/", "/private/files/", 1)
	return None


def normalize_file_url(file_url: str) -> str:
	file_url = cstr(file_url).strip()
	if file_url.startswith("/private/files/"):
		return "/private/files/" + quote(unquote(file_url.rsplit("/", 1)[-1]))
	if file_url.startswith("/files/"):
		return "/files/" + quote(unquote(file_url.rsplit("/", 1)[-1]))
	return file_url


def is_local_file_url(file_url: str) -> bool:
	return cstr(file_url).startswith(LOCAL_FILE_PREFIXES)
