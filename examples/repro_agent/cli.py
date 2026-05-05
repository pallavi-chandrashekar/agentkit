"""repro-agent CLI."""
import asyncio
import sys
from pathlib import Path

from rich.console import Console
from rich.text import Text

from examples.repro_agent.agent import ReproAgent
from examples.repro_agent.library import list_papers

console = Console()


def _format_step(step) -> Text:
    icons = {
        "task": ("[bold cyan]paper[/]", "[paper]"),
        "plan": ("[yellow]plan[/]", "[plan] "),
        "action": ("[blue]act[/]", "[act]   "),
        "observation": ("[dim]obs[/]", "[obs]   "),
        "answer": ("[bold green]done[/]", "[done] "),
    }
    label, _ = icons.get(step.type, (f"[{step.type}]", f"[{step.type}]"))
    text = Text.from_markup(f"  {label} ")
    text.append(step.content or "", style="default")
    return text


async def _run(request: str, workspace: Path, verbose: bool, trace_dir: Path | None) -> int:
    def on_step(step):
        console.print(_format_step(step))

    agent = ReproAgent(
        workspace_path=workspace,
        on_step=on_step if verbose else None,
        trace_dir=trace_dir,
    )

    if not verbose:
        console.print(f"[dim]Reproducing: {request}[/]\n")
    result = await agent.reproduce(request)

    console.print()
    console.print("[bold]Reproduction summary:[/]")
    console.print(result.answer)
    console.print()
    console.print(f"[bold]Files written to {workspace}:[/]")
    for f in agent.list_outputs():
        console.print(f"  • {f}")
    console.print()
    console.print(f"[dim]{result.summary()}[/]")
    if result.trace_path:
        console.print(f"[dim]Trace: {result.trace_path}[/]")
    return 0 if result.success else 1


def main() -> None:
    args = sys.argv[1:]
    if not args or args[0] in ("-h", "--help"):
        print("Usage: repro-agent [--workspace DIR] [--verbose] <paper_id_or_request>")
        print()
        print("Built-in papers:")
        for p in list_papers():
            print(f"  {p['id']:32} — {p['title']}")
        print()
        print("Examples:")
        print('  repro-agent attention_is_all_you_need')
        print('  repro-agent --verbose docaware')
        print('  repro-agent --workspace ./out "Reproduce the few useful things paper"')
        sys.exit(0)

    workspace = Path("./repro_workspace")
    verbose = False
    trace_dir: Path | None = None
    request_parts = []
    i = 0
    while i < len(args):
        if args[i] == "--workspace" and i + 1 < len(args):
            workspace = Path(args[i + 1])
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
            request_parts.append(args[i])
            i += 1

    if not request_parts:
        console.print("[red]Provide a paper id or request[/]")
        sys.exit(1)

    request = " ".join(request_parts)
    sys.exit(asyncio.run(_run(request, workspace, verbose, trace_dir)))


if __name__ == "__main__":
    main()
