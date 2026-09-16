"""Backfill personalized suggestions created while the report agent had no model."""

from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent
DB_PATH = ROOT / "data" / "ai_bole_core_v1.db"
sys.path.insert(0, str(ROOT.parent / "report-agent"))

from reflection import normalize_suggestions  # noqa: E402


def answer_references(suggestion: dict, questions: list[dict], answers: list[dict], kind: str) -> list[list[dict[str, str]]]:
    question_by_id = {str(item.get("id", "")): str(item.get("question", "")).strip() for item in questions}
    answer_by_id = {}
    for item in answers:
        selected, extra = str(item.get("selected", "")).strip(), str(item.get("text", "")).strip()
        answer_by_id[str(item.get("question_id", ""))] = "；".join(value for value in (selected, extra) if value)
    suggestions = suggestion.get(f"{kind}_suggestions", [])
    sources = suggestion.get(f"{kind}_suggestion_sources", [])
    return [[
        {"question": question_by_id[ref], "answer": answer_by_id[ref]}
        for ref in (sources[index] if index < len(sources) else [])
        if ref in question_by_id and answer_by_id.get(ref) and answer_by_id[ref] != "没注意过"
    ] for index in range(len(suggestions))]


def main() -> None:
    with sqlite3.connect(DB_PATH) as db:
        db.row_factory = sqlite3.Row
        rows = db.execute("""SELECT pf.*, cp.display_name FROM parent_feedback pf
                             JOIN child_profiles cp ON cp.id=pf.child_profile_id
                             ORDER BY pf.created_at""").fetchall()
        reports: dict[str, list[tuple[sqlite3.Row, dict]]] = {}
        for row in rows:
            questions, answers = json.loads(row["questions_json"]), json.loads(row["answers_json"])
            current = json.loads(row["suggestion_json"])
            if not str(current.get("consistency", {}).get("text", "")).strip():
                current = normalize_suggestions({}, row["display_name"], answers, questions, {"key": row["dimension_key"]})
            current["family_parent_answer_refs"] = answer_references(current, questions, answers, "family")
            current["teacher_parent_answer_refs"] = answer_references(current, questions, answers, "teacher")
            db.execute("UPDATE parent_feedback SET suggestion_json=? WHERE id=?", (json.dumps(current, ensure_ascii=False), row["id"]))
            reports.setdefault(row["report_id"], []).append((row, current))
        for report_id, feedback in reports.items():
            report_row = db.execute("SELECT report_json,child_profile_id,evidence_set_hash FROM reports WHERE id=?", (report_id,)).fetchone()
            if not report_row:
                continue
            report = json.loads(report_row["report_json"])
            if "base_recommendations" not in report:
                candidates = db.execute("""SELECT report_json FROM reports
                                           WHERE child_profile_id=? AND evidence_set_hash=? AND id<>?
                                           ORDER BY generated_at DESC""", (report_row["child_profile_id"], report_row["evidence_set_hash"], report_id)).fetchall()
                base = next((json.loads(item["report_json"]).get("recommendations") for item in candidates if not json.loads(item["report_json"]).get("feedback_completed")), None)
                report["base_recommendations"] = base or report.get("recommendations", {})
            personalized = report.setdefault("personalized_recommendations", {})
            for row, suggestion in feedback:
                personalized[row["dimension_key"]] = suggestion
            def advice_list(value) -> list[str]:
                return [str(item).strip() for item in (value if isinstance(value, list) else [value]) if str(item).strip()]
            base_family = advice_list(report["base_recommendations"].get("family", []))[:4]
            base_teacher = advice_list(report["base_recommendations"].get("teacher", []))[:4]
            def auxiliary(kind: str, limit: int) -> list[tuple[str, list[dict[str, str]]]]:
                result, used_sources = [], set()
                for value in personalized.values():
                    suggestions = value.get(f"{kind}_suggestions", [])
                    sources = value.get(f"{kind}_parent_answer_refs", [])
                    for index, text in enumerate(suggestions):
                        refs = sources[index] if index < len(sources) else []
                        source_key = tuple((ref.get("question", ""), ref.get("answer", "")) for ref in refs)
                        if refs and source_key not in used_sources and all(text != prior[0] for prior in result):
                            result.append((text, refs))
                            used_sources.add(source_key)
                            if len(result) >= limit:
                                return result
                return result
            family_aux, teacher_aux = auxiliary("family", 2), auxiliary("teacher", 1)
            report["recommendations"]["family"] = base_family + [item[0] for item in family_aux]
            report["recommendations"]["teacher"] = base_teacher + [item[0] for item in teacher_aux]
            report["recommendation_attributions"] = {"family": [[] for _ in base_family] + [item[1] for item in family_aux], "teacher": [[] for _ in base_teacher] + [item[1] for item in teacher_aux]}
            db.execute("UPDATE reports SET report_json=? WHERE id=?", (json.dumps(report, ensure_ascii=False), report_id))
        print(f"Backfilled {len(rows)} parent feedback records across {len(reports)} reports.")


if __name__ == "__main__":
    main()
