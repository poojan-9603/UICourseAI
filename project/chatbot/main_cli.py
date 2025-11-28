from rich.console import Console
from rich.prompt import Prompt
from rich.table import Table
import logging
import os

from chatbot.intent import parse
from chatbot.llm_intent import parse_with_llm
from chatbot.actions import rank_professors, details_section

console = Console()
log = logging.getLogger("chatbot.cli")


def _print_rankings(rows, polarity: str, explain: bool, params):
    if not rows:
        console.print(
            "[yellow]No matching results. Try adjusting subject, course number, keywords, or recency.[/yellow]"
        )
        if explain:
            console.print(f"[dim]Explain filters used: {params}[/dim]")
        return

    header = (
        "😌 Easier/lenient picks (higher A%, lower D/F/W):"
        if polarity == "easy"
        else "💪 Strict/Harder picks (higher D/F/W, lower A%):"
    )
    console.print(header)

    tbl = Table(show_header=True, header_style="bold")
    tbl.add_column("Course")
    tbl.add_column("Instructor")
    tbl.add_column("Sem")
    tbl.add_column("A%")
    tbl.add_column("DFW%")
    tbl.add_column("Students")

    for r in rows:
        tbl.add_row(
            f"{r['subject']} {r['class_num']} — {r['class_title']}",
            r["instructor"],
            r.get("semester") or "",
            f"{r['A_rate']:.1f}",
            f"{r['DFW_rate']:.1f}",
            str(r["total_students"]),
        )
    console.print(tbl)

    if explain:
        console.print(
            f"[dim]Why these? Sorted by "
            f"{'A% desc, DFW% asc' if polarity == 'easy' else 'DFW% desc, A% asc'}, "
            f"then enrollment and recency. Filters: {params}[/dim]"
        )


def _print_details(rows):
    if not rows:
        console.print("[yellow]No matching sections for details.[/yellow]")
        return

    console.print("🔎 Semester-by-semester (most recent first):")
    tbl = Table(show_header=True, header_style="bold")
    for col in ["Semester", "Course", "Instructor", "A%", "DFW%", "Students"]:
        tbl.add_column(col)
    for r in rows:
        tbl.add_row(
            r["semester"],
            f"{r['subject']} {r['class_num']} — {r['class_title']}",
            r["instructor"],
            f"{r['A_rate']:.1f}",
            f"{r['DFW_rate']:.1f}",
            str(r["total_students"]),
        )
    console.print(tbl)


def get_intent(text: str):
    """
    Decide whether to use rule-based parser or LLM-based parser.
    Toggle with environment variable: USE_LLM_INTENT=1
    """
    use_llm = os.getenv("USE_LLM_INTENT") == "1"

    if use_llm:
        console.print("[dim]🔮 Using LLM intent parser...[/dim]")
        try:
            return parse_with_llm(text)
        except Exception as e:
            console.print(
                f"[yellow]⚠️ LLM parser failed, falling back to rule parser: {e}[/yellow]"
            )
            return parse(text)
    else:
        return parse(text)


def handle_text(text: str):
    params = get_intent(text)

    if params.get("details"):
        # e.g., "details cs 580 yu"
        subj = params.get("subject")
        cnum = params.get("class_num")
        inst = params.get("instructor_like") or ""
        rows = details_section(subj or "", cnum or "", inst)
        _print_details(rows)
        return

    rows = rank_professors(params, top_n=5)
    _print_rankings(
        rows,
        params.get("polarity", "easy"),
        params.get("explain", False),
        params,
    )


def main():
    console.print("[bold]UICourseAI Chatbot — MVP[/bold]")
    console.print(
        "Type queries like: 'easy cs 580', 'hard cs 580', 'show easy ml courses', "
        "'easy data cs', 'easy cs 580 recent'"
    )
    console.print("Type 'help' for tips. Type 'exit' to quit.\n")

    while True:
        user = Prompt.ask("You")
        if user.strip().lower() in {"exit", "quit"}:
            break
        if user.strip().lower() == "help":
            console.print(
                "Examples:\n"
                "  • easy cs 580\n"
                "  • hard cs electives 500-level recent\n"
                "  • show easy ml courses\n"
                "  • details cs 580 yu\n"
                "Flags:\n"
                "  • --explain  (prints why a result ranked)\n\n"
                "LLM mode:\n"
                "  • Set USE_LLM_INTENT=1 in your environment to use the AI intent parser."
            )
            continue
        handle_text(user)


if __name__ == "__main__":
    main()
