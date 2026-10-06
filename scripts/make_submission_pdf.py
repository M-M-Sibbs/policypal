"""Create the one-page submission PDF required by the brief: a link to the
GitHub repository and a link to the demo video (plus the live app details).

    pip install reportlab
    python scripts/make_submission_pdf.py ^
        --repo https://github.com/OWNER/REPO ^
        --video https://youtu.be/XXXX ^
        --members "Munashe Sibanda" "Tapiwa Mathew Muwomo" ^
        --admin-token YOUR_TOKEN

(On macOS/Linux use \\ instead of ^ for line continuation.) Output:
submission/PolicyPal_Submission.pdf. The admin token appears only in the PDF,
never in the repository: the submission/ folder is git-ignored.
"""
from __future__ import annotations

import argparse
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_APP = "https://policypal-8u6n.onrender.com"


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Build the PolicyPal submission PDF")
    parser.add_argument("--repo", required=True, help="GitHub repository URL (shared with quantic-grader)")
    parser.add_argument("--video", required=True, help="Demo video URL (5-10 minutes)")
    parser.add_argument("--members", nargs="+", default=["Munashe Sibanda", "Tapiwa Mathew Muwomo"])
    parser.add_argument("--app", default=DEFAULT_APP, help="Live application URL")
    parser.add_argument("--admin-token", default="", help="Token for the /admin page (optional)")
    parser.add_argument("--out", default=str(ROOT / "submission" / "PolicyPal_Submission.pdf"))
    args = parser.parse_args(argv)

    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
        from reportlab.lib.units import cm
        from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
    except ImportError:
        print("reportlab is not installed. Run: pip install reportlab")
        return 1

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    styles = getSampleStyleSheet()
    title = ParagraphStyle("T", parent=styles["Title"], fontSize=20, spaceAfter=4)
    sub = ParagraphStyle("S", parent=styles["Normal"], fontSize=11, textColor="#555555", alignment=1, spaceAfter=18)
    h = ParagraphStyle("H", parent=styles["Heading2"], fontSize=13, spaceBefore=14, spaceAfter=6)
    body = ParagraphStyle("B", parent=styles["Normal"], fontSize=10.5, leading=15)
    cell = ParagraphStyle("C", parent=body, fontSize=10.5)

    def link(url: str) -> str:
        return f'<link href="{url}" color="#0f766e"><u>{url}</u></link>'

    rows = [
        [Paragraph("<b>1. GitHub repository</b>", cell), Paragraph(link(args.repo), cell)],
        [Paragraph("<b>2. Demo video</b>", cell), Paragraph(link(args.video), cell)],
    ]
    table = Table(rows, colWidths=[4.5 * cm, 12 * cm])
    table.setStyle(
        TableStyle(
            [
                ("GRID", (0, 0), (-1, -1), 0.5, "#cccccc"),
                ("BACKGROUND", (0, 0), (0, -1), "#f0f4f7"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ]
        )
    )

    story = [
        Paragraph("PolicyPal — Company Policy Assistant", title),
        Paragraph(f"AI Engineering Project submission · {date.today().strftime('%d %B %Y')}", sub),
        Paragraph("Submission links", h),
        table,
        Paragraph("Team", h),
        Paragraph(", ".join(args.members), body),
        Paragraph("Live application (optional deployment)", h),
        Paragraph(f"App: {link(args.app)}<br/>Health check: {link(args.app + '/health')}", body),
    ]
    if args.admin_token:
        story += [
            Spacer(1, 4),
            Paragraph(
                f"Policy management: {link(args.app + '/admin')} — admin token: <font face='Courier'>{args.admin_token}</font><br/>"
                "To try a policy update, upload <i>examples/policy-updates/POL-14_pets_in_the_workplace.md</i> from the "
                "repository, ask “Can I bring my dog to the office?”, then click <b>Reset to original policies</b>.",
                body,
            ),
        ]
    story += [
        Paragraph("Notes for the grader", h),
        Paragraph(
            "The repository is shared with the GitHub account <b>quantic-grader</b>. It contains README.md (setup and run "
            "instructions), design-and-evaluation.md, ai-tooling.md, deployed.md and requirements-compliance.md, which maps "
            "each requirement of the brief to its evidence. The free Render instance sleeps when idle; the first request "
            "may take about a minute.",
            body,
        ),
    ]
    SimpleDocTemplate(
        str(out), pagesize=A4, leftMargin=2.2 * cm, rightMargin=2.2 * cm, topMargin=2 * cm, bottomMargin=2 * cm,
        title="PolicyPal submission", author=", ".join(args.members),
    ).build(story)
    print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
