"""data-assistant CLI."""
import asyncio
import sys
from pathlib import Path

from rich.console import Console
from rich.text import Text

from examples.data_assistant.agent import DataAssistant
from examples.data_assistant.seed_db import DEFAULT_DB_PATH, seed_db

console = Console()


def _format_step(step) -> Text:
    """Format an agent Step with color."""
    icons = {
        "task": ("[bold cyan]task[/]", "[task]"),
        "plan": ("[yellow]plan[/]", "[plan]"),
        "action": ("[blue]act[/]", "[act] "),
        "observation": ("[dim]obs[/]", "[obs] "),
        "answer": ("[bold green]ans[/]", "[ans] "),
    }
    label, plain = icons.get(step.type, (f"[{step.type}]", f"[{step.type}]"))
    text = Text.from_markup(f"  {label} ")
    text.append(step.content or "", style="default")
    return text


async def _run(question: str, db_path: Path, verbose: bool, trace_dir: Path | None) -> int:
    if not db_path.exists():
        console.print(f"[yellow]Database not found at {db_path}. Seeding…[/]")
        seed_db(db_path)
        console.print(f"[green]Seeded sample database at {db_path}[/]")

    def on_step(step):
        console.print(_format_step(step))

    assistant = DataAssistant(
        db_path=db_path,
        on_step=on_step if verbose else None,
        trace_dir=trace_dir,
    )

    if not verbose:
        console.print(f"[dim]Asking: {question}[/]\n")
    result = await assistant.ask(question)

    console.print()
    console.print("[bold]Answer:[/]")
    console.print(result.answer)
    console.print()
    console.print(f"[dim]{result.summary()}[/]")
    if result.trace_path:
        console.print(f"[dim]Trace: {result.trace_path}[/]")
    return 0 if result.success else 1


def main() -> None:
    args = sys.argv[1:]
    if not args or args[0] in ("-h", "--help"):
        print("Usage: data-assistant [--db PATH] [--verbose] [--trace [DIR]] <question>")
        print()
        print("Examples:")
        print('  data-assistant "What was our top product last month?"')
        print('  data-assistant --verbose --trace "How many customers signed up?"')
        print('  data-assistant --db /path/to/db.sqlite --trace ./mytraces "What is our total revenue?"')
        sys.exit(0)

    db_path = DEFAULT_DB_PATH
    verbose = False
    trace_dir: Path | None = None
    question_parts = []
    i = 0
    while i < len(args):
        if args[i] == "--db" and i + 1 < len(args):
            db_path = Path(args[i + 1])
            i += 2
        elif args[i] == "--trace":
            if i + 1 < len(args) and not args[i + 1].startswith("-"):
                trace_dir = Path(args[i + 1])
                i += 2
            else:
                trace_dir = Path("./traces")
                i += 1
        elif args[i] in ("--verbose", "-v"):
            verbose = True
            i += 1
        else:
            question_parts.append(args[i])
            i += 1

    if not question_parts:
        console.print("[red]Error: no question provided[/]")
        sys.exit(1)

    question = " ".join(question_parts)
    sys.exit(asyncio.run(_run(question, db_path, verbose, trace_dir)))


if __name__ == "__main__":
    main()
