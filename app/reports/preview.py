"""Offline preview: python -m app.reports.preview demo/example.docx output.pdf."""

import argparse
from pathlib import Path

import yaml

from app.analysis.aggregator import aggregate
from app.document.parser import parse_docx
from app.reports.pdf import build_pdf_report
from app.rules.engine import RuleEngine
from app.rules.models import RulePreset
from app.security.validation import run_all_validations


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("document", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument(
        "--preset", type=Path, default=Path("rules/presets/makhambet_coursework.yaml")
    )
    parser.add_argument("--lang", choices=["ru", "kk", "en"], default="ru")
    args = parser.parse_args()
    if args.document.resolve() == args.output.resolve():
        parser.error("Input and output paths must differ")
    preset = RulePreset.model_validate(yaml.safe_load(args.preset.read_text(encoding="utf-8")))
    run_all_validations(args.document, args.document.name, None)
    checked = RuleEngine().run(parse_docx(args.document), preset, args.lang)
    result = aggregate(checked.findings, [], preset, checked.sections_found, False)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    build_pdf_report(
        result,
        output_path=args.output,
        document_display_name=args.document.name,
        institution=preset.institution,
        work_type_label=preset.name,
        lang=args.lang,
    )
    print(f"{args.output}: {result.score:g}/{result.max_score:g} (AI not evaluated)")


if __name__ == "__main__":
    main()
