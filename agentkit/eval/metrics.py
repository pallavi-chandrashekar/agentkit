"""Aggregate metrics from a list of EvalResults."""
from agentkit.eval.harness import EvalResult


def compute_metrics(results: list[EvalResult]) -> dict:
    """Compute aggregate metrics."""
    if not results:
        return {
            "total": 0, "passed": 0, "success_rate": 0.0,
            "avg_iterations": 0.0, "avg_tool_calls": 0.0,
            "avg_cost_usd": 0.0, "total_cost_usd": 0.0,
            "avg_duration_seconds": 0.0,
        }

    passed_results = [r for r in results if r.passed]
    successful_results = [r for r in results if not r.error]
    n = len(results)

    return {
        "total": n,
        "passed": len(passed_results),
        "failed": n - len(passed_results),
        "errors": n - len(successful_results),
        "success_rate": round(len(passed_results) / n, 3),
        "avg_iterations": round(sum(r.iterations for r in results) / n, 2),
        "avg_tool_calls": round(sum(r.tool_calls for r in results) / n, 2),
        "avg_cost_usd": round(sum(r.cost_usd for r in results) / n, 6),
        "total_cost_usd": round(sum(r.cost_usd for r in results), 4),
        "avg_duration_seconds": round(sum(r.duration_seconds for r in results) / n, 2),
    }


def format_metrics(metrics: dict) -> str:
    """Format metrics as a human-readable string."""
    return (
        f"Cases:       {metrics['total']}\n"
        f"Passed:      {metrics['passed']} ({metrics['success_rate'] * 100:.1f}%)\n"
        f"Failed:      {metrics['failed']}\n"
        f"Errors:      {metrics['errors']}\n"
        f"Avg iter:    {metrics['avg_iterations']}\n"
        f"Avg tools:   {metrics['avg_tool_calls']}\n"
        f"Avg cost:    ${metrics['avg_cost_usd']:.4f}\n"
        f"Total cost:  ${metrics['total_cost_usd']:.4f}\n"
        f"Avg time:    {metrics['avg_duration_seconds']}s"
    )
