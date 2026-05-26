"""Clean-merge selected Frappe app data between sites in this bench.

Typical usage:

Dry-run Slides into Drive:
bench --site drive-frappe-replica execute frappe.clean_merge_sites.execute --kwargs "{'source_site':'slides-frappe-replica','target_site':'drive-frappe-replica','profile':'slides','dry_run':1}"

Apply Slides into Drive:
bench --site drive-frappe-replica execute frappe.clean_merge_sites.execute --kwargs "{'source_site':'slides-frappe-replica','target_site':'drive-frappe-replica','profile':'slides','dry_run':0}"

Dry-run Drive + Slides + Writer into Suite:
bench --site suite-frappe-replica execute frappe.clean_merge_sites.execute --kwargs "{'source_site':'drive-frappe-replica','target_site':'suite-frappe-replica','profile':'drive_suite','dry_run':1}"

This is intentionally conservative:
- existing target docs with the same name are skipped only if byte-for-byte equal
- different existing target docs are reported as conflicts and abort the merge
- existing target file paths with different bytes are reported as conflicts
- app hooks are bypassed so imports do not create surprise side effects
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import sys
from copy import deepcopy
from pathlib import Path
from typing import Any
from urllib.parse import quote, unquote


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

SLIDES_DOCTYPES = ["Presentation"]

DRIVE_DOCTYPES = [
	"Drive Team",
	"Drive Tag",
	"Drive Document",
	"Drive Document Version",
	"Drive File",
	"Drive Permission",
	"Drive Favourite",
	"Drive Notification",
	"Drive Transfer",
	"Drive Desktop Client",
	"Drive User Invitation",
	"Account Request",
	"Drive Entity Activity Log",
	"Drive Entity Log",
	"Drive Settings",
	"Drive Disk Settings",
]

WRITER_DOCTYPES = [
	"Writer Template",
	"Writer Document",
	"Writer Version",
]

PROFILES = {
	"slides": SLIDES_DOCTYPES,
	"drive": DRIVE_DOCTYPES,
	"drive_suite": SLIDES_DOCTYPES + WRITER_DOCTYPES + DRIVE_DOCTYPES,
}

LOCAL_FILE_URL_RE = re.compile(r'/(?:private/)?files/[^"\'\s<>)]+')
LOCAL_FILE_PREFIXES = ("/files/", "/private/files/")


def execute(
	source_site: str,
	target_site: str,
	profile: str = "slides",
	doctypes: list[str] | str | None = None,
	ignore_names: list[str] | str | None = None,
	overwrite_singles: list[str] | str | None = None,
	dry_run: int = 1,
	commit_every: int = 100,
) -> dict[str, Any]:
	"""Merge selected data from source_site into target_site.

	Args:
		source_site: Existing source site name.
		target_site: Existing target site name.
		profile: One of slides, drive, drive_suite. Ignored when doctypes is set.
		doctypes: Optional explicit list, or comma-separated DocType names.
		ignore_names: Optional document names to exclude from export.
		overwrite_singles: Optional Single DocType names to overwrite on target.
		dry_run: 1 checks and prints the plan. 0 applies the merge.
		commit_every: Commit after this many inserted parent documents.
	"""
	dry_run = cint(dry_run)
	selected_doctypes = normalize_doctypes(profile, doctypes)
	ignored_names = normalize_names(ignore_names)
	singles_to_overwrite = normalize_names(overwrite_singles)

	print(f"Source: {source_site}")
	print(f"Target: {target_site}")
	print(f"DocTypes: {', '.join(selected_doctypes)}")
	if ignored_names:
		print(f"Ignoring names: {', '.join(sorted(ignored_names))}")
	if singles_to_overwrite:
		print(f"Overwriting Singles: {', '.join(sorted(singles_to_overwrite))}")
	print(f"Mode: {'dry-run' if dry_run else 'apply'}")

	source_bundle = export_site_bundle(source_site, selected_doctypes, ignored_names)
	target_report = inspect_target(target_site, source_bundle)

	print_report(source_bundle, target_report)

	if target_report["doc_conflicts"] or target_report["file_conflicts"]:
		raise RuntimeError("Conflicts found. Resolve them before applying this merge.")

	if dry_run:
		return {
			"status": "dry_run",
			"export": source_bundle["counts"],
			"target": summarize_report(target_report),
		}

	apply_bundle(
		target_site,
		source_site,
		source_bundle,
		target_report,
		commit_every=commit_every,
		overwrite_singles=singles_to_overwrite,
	)
	print("Merge completed.")
	return {"status": "merged", "export": source_bundle["counts"], "target": summarize_report(target_report)}


def compare_docs(source_site: str, target_site: str, doctype: str, names: list[str] | str) -> dict[str, Any]:
	"""Print a compact field-level diff for documents present on both sites."""
	if isinstance(names, str):
		names = [name.strip() for name in names.split(",") if name.strip()]

	source_docs = {}
	target_docs = {}

	connect(source_site)
	try:
		for name in names:
			if frappe.db.exists(doctype, name):
				source_docs[name] = plain_dict(frappe.get_doc(doctype, name).as_dict(no_nulls=False))
	finally:
		disconnect()

	connect(target_site)
	try:
		for name in names:
			if frappe.db.exists(doctype, name):
				target_docs[name] = plain_dict(frappe.get_doc(doctype, name).as_dict(no_nulls=False))
	finally:
		disconnect()

	result = {}
	for name in names:
		source_doc = source_docs.get(name)
		target_doc = target_docs.get(name)
		if not source_doc or not target_doc:
			result[name] = {
				"source_exists": bool(source_doc),
				"target_exists": bool(target_doc),
				"diffs": [],
			}
			continue

		diffs = diff_values(source_doc, target_doc)
		result[name] = {
			"source_exists": True,
			"target_exists": True,
			"diff_count": len(diffs),
			"diffs": diffs[:200],
			"truncated": len(diffs) > 200,
		}

	print(json.dumps(result, indent=2, default=str, ensure_ascii=False))
	return result


def normalize_doctypes(profile: str, doctypes: list[str] | str | None) -> list[str]:
	if doctypes:
		if isinstance(doctypes, str):
			return [doctype.strip() for doctype in doctypes.split(",") if doctype.strip()]
		return list(doctypes)

	if profile not in PROFILES:
		frappe.throw(f"Unknown profile {profile!r}. Use one of: {', '.join(sorted(PROFILES))}")
	return PROFILES[profile]


def normalize_names(names: list[str] | str | None) -> set[str]:
	if not names:
		return set()
	if isinstance(names, str):
		return {name.strip() for name in names.split(",") if name.strip()}
	return {name.strip() for name in names if name and name.strip()}


def export_site_bundle(
	site: str, doctypes: list[str], ignored_names: set[str] | None = None
) -> dict[str, Any]:
	ignored_names = ignored_names or set()
	connect(site)
	try:
		docs_by_doctype: dict[str, list[dict[str, Any]]] = {}
		singles: dict[str, dict[str, Any]] = {}
		counts: dict[str, int] = {}
		exported_doc_keys: set[tuple[str, str]] = set()

		for doctype in doctypes:
			if not frappe.db.exists("DocType", doctype):
				print(f"Skipping missing source DocType: {doctype}")
				continue

			meta = frappe.get_meta(doctype)
			if meta.istable:
				print(f"Skipping child table DocType; exported through parents: {doctype}")
				continue

			if meta.issingle:
				data = export_single(doctype)
				singles[doctype] = data
				counts[doctype] = 1
				continue

			names = [
				name
				for name in frappe.get_all(doctype, pluck="name", order_by="creation asc, name asc")
				if name not in ignored_names
			]
			docs = []
			for name in names:
				doc = frappe.get_doc(doctype, name).as_dict(no_nulls=False)
				doc = plain_dict(doc)
				docs.append(doc)
				collect_doc_keys(doc, exported_doc_keys)

			docs_by_doctype[doctype] = docs
			counts[doctype] = len(docs)

		file_docs = export_related_files(docs_by_doctype, singles, exported_doc_keys)
		counts["File"] = len(file_docs)
		return {
			"site": site,
			"doctypes": doctypes,
			"docs": docs_by_doctype,
			"singles": singles,
			"files": file_docs,
			"counts": counts,
		}
	finally:
		disconnect()


def export_single(doctype: str) -> dict[str, Any]:
	doc = {"doctype": doctype, "name": doctype}
	for field in frappe.get_meta(doctype).fields:
		if field.fieldtype not in frappe.model.no_value_fields:
			doc[field.fieldname] = frappe.db.get_single_value(doctype, field.fieldname)
	return plain_dict(doc)


def export_related_files(
	docs_by_doctype: dict[str, list[dict[str, Any]]],
	singles: dict[str, dict[str, Any]],
	exported_doc_keys: set[tuple[str, str]],
) -> list[dict[str, Any]]:
	file_urls = set()

	for docs in docs_by_doctype.values():
		for doc in docs:
			file_urls.update(find_local_file_urls(doc))

	for single in singles.values():
		file_urls.update(find_local_file_urls(single))

	file_names = set()
	if file_urls:
		file_names.update(
			frappe.get_all(
				"File",
				filters={"file_url": ["in", sorted(file_urls)]},
				pluck="name",
			)
		)

	for doctype, name in exported_doc_keys:
		file_names.update(
			frappe.get_all(
				"File",
				filters={"attached_to_doctype": doctype, "attached_to_name": name},
				pluck="name",
			)
		)

	file_docs = []
	for name in sorted(file_names):
		file_doc = frappe.get_doc("File", name).as_dict(no_nulls=False)
		file_docs.append(plain_dict(file_doc))
	return file_docs


def inspect_target(target_site: str, bundle: dict[str, Any]) -> dict[str, Any]:
	connect(target_site)
	try:
		report = {
			"missing_docs": [],
			"identical_docs": [],
			"doc_conflicts": [],
			"missing_singles": [],
			"changed_singles": [],
			"identical_singles": [],
			"missing_files": [],
			"identical_files": [],
			"file_conflicts": [],
		}

		for doctype, doc in bundle["singles"].items():
			if not frappe.db.exists("DocType", doctype):
				report["missing_singles"].append((doctype, "missing target DocType"))
				continue
			target_single = export_single(doctype)
			if canonical_doc(doc) == canonical_doc(target_single):
				report["identical_singles"].append(doctype)
			else:
				report["changed_singles"].append(doctype)

		all_docs = []
		for docs in bundle["docs"].values():
			for doc in docs:
				all_docs.extend(flatten_doc(doc))
		for file_doc in bundle["files"]:
			all_docs.extend(flatten_doc(file_doc))

		for doc in all_docs:
			doctype = doc["doctype"]
			name = doc["name"]
			if not frappe.db.exists("DocType", doctype):
				report["doc_conflicts"].append((doctype, name, "missing target DocType"))
				continue
			if not frappe.db.exists(doctype, name):
				report["missing_docs"].append((doctype, name))
				continue

			target_doc = frappe.get_doc(doctype, name).as_dict(no_nulls=False)
			if canonical_doc(doc) == canonical_doc(plain_dict(target_doc)):
				report["identical_docs"].append((doctype, name))
			else:
				report["doc_conflicts"].append((doctype, name, "different target document exists"))

		for file_doc in bundle["files"]:
			file_url = file_doc.get("file_url")
			if not is_local_file_url(file_url):
				continue
			source_path = get_site_file_path(bundle["site"], file_url)
			target_path = get_site_file_path(target_site, file_url)
			if not target_path.exists():
				report["missing_files"].append(file_url)
			elif same_file(source_path, target_path):
				report["identical_files"].append(file_url)
			else:
				report["file_conflicts"].append((file_url, "different target file exists"))

		return report
	finally:
		disconnect()


def apply_bundle(
	target_site: str,
	source_site: str,
	bundle: dict[str, Any],
	report: dict[str, Any],
	commit_every: int,
	overwrite_singles: set[str] | None = None,
) -> None:
	overwrite_singles = overwrite_singles or set()
	connect(target_site)
	try:
		for file_url in report["missing_files"]:
			copy_site_file(source_site, target_site, file_url)

		inserted = 0
		for doctype, single in bundle["singles"].items():
			if doctype in report["changed_singles"] and doctype not in overwrite_singles:
				print(f"Skipping changed Single {doctype}; update it manually after review.")
				continue
			if doctype in report["missing_singles"]:
				continue
			update_single(single)
			if doctype in overwrite_singles:
				print(f"Overwrote Single {doctype}.")

		for file_doc in bundle["files"]:
			if insert_missing_doc_tree(file_doc):
				inserted += 1
				if inserted % commit_every == 0:
					frappe.db.commit()

		for docs in bundle["docs"].values():
			for doc in docs:
				if insert_missing_doc_tree(doc):
					inserted += 1
					if inserted % commit_every == 0:
						frappe.db.commit()

		frappe.db.commit()
		print(f"Inserted {inserted} parent document(s).")
	finally:
		disconnect()


def insert_missing_doc_tree(doc_data: dict[str, Any]) -> bool:
	doctype = doc_data["doctype"]
	name = doc_data["name"]
	if frappe.db.exists(doctype, name):
		return False

	doc = frappe.get_doc(deepcopy(doc_data))
	db_insert_tree(doc)
	return True


def db_insert_tree(doc) -> None:
	doc.flags.ignore_links = True
	doc.flags.ignore_permissions = True
	doc.db_insert()

	for field in doc.meta.get_table_fields():
		for index, child in enumerate(doc.get(field.fieldname) or [], start=1):
			child.parent = doc.name
			child.parenttype = doc.doctype
			child.parentfield = field.fieldname
			child.idx = child.idx or index
			db_insert_tree(child)


def update_single(single: dict[str, Any]) -> None:
	doctype = single["doctype"]
	if not frappe.db.exists("DocType", doctype):
		return

	for fieldname, value in single.items():
		if fieldname in {"doctype", "name"}:
			continue
		frappe.db.set_single_value(doctype, fieldname, value, update_modified=False)


def print_report(bundle: dict[str, Any], report: dict[str, Any]) -> None:
	print("Exported:")
	for doctype, count in bundle["counts"].items():
		print(f"- {doctype}: {count}")

	print("Target check:")
	print(f"- missing docs to insert: {len(report['missing_docs'])}")
	print(f"- identical docs to skip: {len(report['identical_docs'])}")
	print(f"- doc conflicts: {len(report['doc_conflicts'])}")
	print(f"- missing files to copy: {len(report['missing_files'])}")
	print(f"- identical files to skip: {len(report['identical_files'])}")
	print(f"- file conflicts: {len(report['file_conflicts'])}")
	print(f"- changed Singles skipped: {len(report['changed_singles'])}")

	for title, rows in (
		("Doc conflicts", report["doc_conflicts"]),
		("File conflicts", report["file_conflicts"]),
		("Changed Singles", report["changed_singles"]),
	):
		if rows:
			print(title + ":")
			for row in rows[:50]:
				print(f"  - {row}")
			if len(rows) > 50:
				print(f"  ... {len(rows) - 50} more")


def summarize_report(report: dict[str, Any]) -> dict[str, int]:
	return {key: len(value) for key, value in report.items()}


def flatten_doc(doc: dict[str, Any]) -> list[dict[str, Any]]:
	items = [doc]
	for value in doc.values():
		if isinstance(value, list):
			for child in value:
				if isinstance(child, dict) and child.get("doctype") and child.get("name"):
					items.extend(flatten_doc(child))
	return items


def collect_doc_keys(doc: dict[str, Any], keys: set[tuple[str, str]]) -> None:
	keys.add((doc["doctype"], doc["name"]))
	for value in doc.values():
		if isinstance(value, list):
			for child in value:
				if isinstance(child, dict) and child.get("doctype") and child.get("name"):
					collect_doc_keys(child, keys)


def find_local_file_urls(value: Any) -> set[str]:
	text = json.dumps(value, default=str, ensure_ascii=False)
	urls = set()
	for match in LOCAL_FILE_URL_RE.findall(text):
		urls.add(normalize_file_url(match.rstrip(".,;:")))
	return urls


def normalize_file_url(file_url: str | None) -> str:
	file_url = (file_url or "").strip()
	if file_url.startswith("/private/files/"):
		return "/private/files/" + quote(unquote(file_url.rsplit("/", 1)[-1]))
	if file_url.startswith("/files/"):
		return "/files/" + quote(unquote(file_url.rsplit("/", 1)[-1]))
	return file_url


def is_local_file_url(file_url: str | None) -> bool:
	return bool(file_url) and str(file_url).startswith(LOCAL_FILE_PREFIXES)


def get_site_file_path(site: str, file_url: str) -> Path:
	file_name = unquote(file_url.rsplit("/", 1)[-1])
	if file_url.startswith("/private/files/"):
		return SITES_PATH / site / "private" / "files" / file_name
	if file_url.startswith("/files/"):
		return SITES_PATH / site / "public" / "files" / file_name
	frappe.throw(f"Unsupported local file URL: {file_url}")


def copy_site_file(source_site: str, target_site: str, file_url: str) -> None:
	source_path = get_site_file_path(source_site, file_url)
	target_path = get_site_file_path(target_site, file_url)
	if not source_path.exists():
		print(f"Warning: source file missing on disk, skipped copy: {source_path}")
		return
	target_path.parent.mkdir(parents=True, exist_ok=True)
	shutil.copy2(source_path, target_path)


def same_file(left: Path, right: Path) -> bool:
	if not left.exists() or not right.exists():
		return False
	if left.stat().st_size != right.stat().st_size:
		return False
	return file_sha256(left) == file_sha256(right)


def file_sha256(path: Path) -> str:
	digest = hashlib.sha256()
	with path.open("rb") as file_obj:
		for chunk in iter(lambda: file_obj.read(1024 * 1024), b""):
			digest.update(chunk)
	return digest.hexdigest()


def canonical_doc(doc: dict[str, Any]) -> str:
	return json.dumps(plain_dict(doc), sort_keys=True, default=str, separators=(",", ":"))


def plain_dict(value: Any) -> Any:
	if isinstance(value, dict):
		return {key: plain_dict(item) for key, item in value.items()}
	if isinstance(value, list):
		return [plain_dict(item) for item in value]
	return value


def diff_values(source: Any, target: Any, path: str = "") -> list[dict[str, Any]]:
	if isinstance(source, dict) and isinstance(target, dict):
		diffs = []
		for key in sorted(set(source) | set(target)):
			next_path = f"{path}.{key}" if path else key
			if key not in source:
				diffs.append(
					{"path": next_path, "source": "<missing>", "target": summarize_value(target[key])}
				)
			elif key not in target:
				diffs.append(
					{"path": next_path, "source": summarize_value(source[key]), "target": "<missing>"}
				)
			else:
				diffs.extend(diff_values(source[key], target[key], next_path))
		return diffs

	if isinstance(source, list) and isinstance(target, list):
		diffs = []
		if len(source) != len(target):
			diffs.append({"path": f"{path}.length", "source": len(source), "target": len(target)})
		for index, (source_item, target_item) in enumerate(zip(source, target, strict=False)):
			diffs.extend(diff_values(source_item, target_item, f"{path}[{index}]"))
		return diffs

	if source != target:
		return [{"path": path, "source": summarize_value(source), "target": summarize_value(target)}]

	return []


def summarize_value(value: Any) -> Any:
	if isinstance(value, str) and len(value) > 300:
		return value[:300] + f"... <{len(value)} chars>"
	if isinstance(value, list):
		return f"<list len={len(value)}>"
	if isinstance(value, dict):
		return f"<dict keys={len(value)}>"
	return value


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


def main() -> None:
	import argparse

	parser = argparse.ArgumentParser(description="Clean-merge selected Frappe app data between sites.")
	parser.add_argument("--source-site", required=True)
	parser.add_argument("--target-site", required=True)
	parser.add_argument("--profile", default="slides", choices=sorted(PROFILES))
	parser.add_argument("--doctypes", help="Comma-separated explicit DocType list.")
	parser.add_argument("--apply", action="store_true", help="Apply the merge. Default is dry-run.")
	parser.add_argument("--commit-every", type=int, default=100)
	args = parser.parse_args()

	execute(
		source_site=args.source_site,
		target_site=args.target_site,
		profile=args.profile,
		doctypes=args.doctypes,
		dry_run=0 if args.apply else 1,
		commit_every=args.commit_every,
	)


if __name__ == "__main__":
	main()
