"""agentkit-trace CLI — render a JSONL trace file as HTML."""
import sys
from pathlib import Path

from agentkit.observability.viewer import render_trace_html


def main() -> None:
    args = sys.argv[1:]
    if not args or args[0] in ("-h", "--help"):
        print("Usage: agentkit-trace <trace.jsonl> [--out OUTPUT.html] [--title TITLE]")
        print()
        print("Examples:")
        print("  agentkit-trace traces/run_1730900000.jsonl")
        print("  agentkit-trace traces/latest.jsonl --out report.html")
        sys.exit(0)

    trace_path = None
    output_path: Path | None = None
    title = "Agent trace"
    i = 0
    while i < len(args):
        if args[i] == "--out" and i + 1 < len(args):
            output_path = Path(args[i + 1])
            i += 2
        elif args[i] == "--title" and i + 1 < len(args):
            title = args[i + 1]
            i += 2
        elif args[i].startswith("-"):
            print(f"Unknown flag: {args[i]}", file=sys.stderr)
            sys.exit(2)
        else:
            trace_path = Path(args[i])
            i += 1

    if not trace_path:
        print("Provide a trace file path", file=sys.stderr)
        sys.exit(1)

    try:
        out = render_trace_html(trace_path, output_path=output_path, title=title)
        print(f"Wrote {out}")
    except (FileNotFoundError, ValueError) as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
