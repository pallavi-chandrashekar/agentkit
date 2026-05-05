"""pipeline-doctor CLI."""
import asyncio
import sys
from pathlib import Path

from rich.console import Console
from rich.text import Text

from examples.pipeline_doctor.agent import PipelineDoctor
from examples.pipeline_doctor.backend import SCENARIOS

console = Console()


def _format_step(step) -> Text:
    icons = {
        "task": ("[bold cyan]alert[/]", "[alert]"),
        "plan": ("[yellow]plan[/]", "[plan] "),
        "action": ("[blue]act[/]", "[act]  "),
        "observation": ("[dim]obs[/]", "[obs]  "),
        "answer": ("[bold green]diag[/]", "[diag] "),
    }
    label, _ = icons.get(step.type, (f"[{step.type}]", f"[{step.type}]"))
    text = Text.from_markup(f"  {label} ")
    text.append(step.content or "", style="default")
    return text


async def _run(alert: str, scenario: str, verbose: bool, trace_dir: Path | None) -> int:
    def on_step(step):
        console.print(_format_step(step))

    doctor = PipelineDoctor(
        scenario=scenario,
        on_step=on_step if verbose else None,
        trace_dir=trace_dir,
    )

    if not verbose:
        console.print(f"[dim]Alert: {alert}[/]\n")
    result = await doctor.diagnose(alert)

    console.print()
    console.print("[bold]Diagnosis:[/]")
    console.print(result.answer)
    console.print()
    console.print(f"[dim]{result.summary()}[/]")
    if result.trace_path:
        console.print(f"[dim]Trace: {result.trace_path}[/]")
    return 0 if result.success else 1


def main() -> None:
    args = sys.argv[1:]
    if not args or args[0] in ("-h", "--help"):
        print("Usage: pipeline-doctor [--scenario NAME] [--verbose] [<alert>]")
        print()
        print("Available scenarios:")
        for name, data in SCENARIOS.items():
            print(f"  {name:18} {data['description']}")
        print()
        print("Examples:")
        print('  pipeline-doctor "orders_etl failed at 03:17 UTC"')
        print('  pipeline-doctor --scenario rate_limit --verbose "customers_sync failing repeatedly"')
        sys.exit(0)

    scenario = "schema_drift"
    verbose = False
    trace_dir: Path | None = None
    alert_parts = []
    i = 0
    while i < len(args):
        if args[i] == "--scenario" and i + 1 < len(args):
            scenario = args[i + 1]
            if scenario not in SCENARIOS:
                console.print(f"[red]Unknown scenario: {scenario}[/]")
                console.print(f"Available: {list(SCENARIOS.keys())}")
                sys.exit(1)
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
            alert_parts.append(args[i])
            i += 1

    if not alert_parts:
        # Default alert based on scenario
        scenario_data = SCENARIOS[scenario]
        first_dag = list(scenario_data["dags"].keys())[0]
        alert_parts = [f"{first_dag} pipeline failed. Investigate and propose a fix."]

    alert = " ".join(alert_parts)
    sys.exit(asyncio.run(_run(alert, scenario, verbose, trace_dir)))


if __name__ == "__main__":
    main()
