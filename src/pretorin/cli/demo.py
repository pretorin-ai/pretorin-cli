"""Demo mode for Pretorin CLI - showcases the analyze feature with JMCP mock data."""

import random
import time

from rich import print as rprint
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from rich.table import Table
from rich.syntax import Syntax

from pretorin.cli.animations import ROMEBOT_COLOR

console = Console()

# JMCP Demo System Info
JMCP_SYSTEM = {
    "name": "Joint Mission Command Platform",
    "short_name": "JMCP",
    "version": "3.2.1",
    "classification": "CUI",
    "agency": "Department of War",
    "framework": "DoD RMF / NIST 800-53",
    "components": [
        "Mission Planning Service",
        "Real-time Telemetry Gateway",
        "Operator Authentication Module",
        "Secure Communications Hub",
        "Audit & Compliance Engine",
    ],
}

# Mock evidence for AC-6 (Least Privilege)
AC6_EVIDENCE = {
    "title": "Least Privilege",
    "component": "Operator Authentication Module",
    "files_scanned": 34,
    "evidence_found": 3,
    "status": "partial",
    "confidence": "high",
    "finding": {
        "file": "src/auth/permissions.py",
        "line": 89,
        "description": "Service account with excessive privileges detected",
        "code": '''# FINDING: Service account 'svc_mission_backup' has admin privileges
# This violates AC-6 (Least Privilege) - backup service should only
# have read access to mission data, not full administrative rights

SERVICE_ACCOUNTS = {
    "svc_mission_backup": {
        "name": "Mission Backup Service",
        "roles": [
            Role.ADMIN,           # EXCESSIVE: Should be Role.BACKUP_OPERATOR
            Role.DATA_EXPORT,     # EXCESSIVE: Not needed for backup
            Role.USER_MANAGEMENT, # EXCESSIVE: Backup doesn't manage users
        ],
        "created": "2024-03-15",
        "last_review": None,  # WARNING: Never reviewed
    },
    "svc_telemetry": {
        "name": "Telemetry Collector",
        "roles": [Role.TELEMETRY_READ],  # Correct: minimal privileges
        "created": "2024-01-10",
        "last_review": "2024-12-01",
    },
}''',
    },
}

MISSION_BANNER = """
[#FF9010]╔════════════════════════════════════════════════════════════════════════╗[/#FF9010]
[#FF9010]║[/#FF9010]   [#EAB536] ∫[/#EAB536]                                                                    [#FF9010]║[/#FF9010]
[#FF9010]║[/#FF9010]   [#EAB536][°□°][/#EAB536]  [bold #FF9010]PRETORIN[/bold #FF9010]                                                    [#FF9010]║[/#FF9010]
[#FF9010]║[/#FF9010]         [dim]Automated Compliance Assessment[/dim]                                [#FF9010]║[/#FF9010]
[#FF9010]╚════════════════════════════════════════════════════════════════════════╝[/#FF9010]
"""


def create_scanning_animation(files_count: int, component: str) -> None:
    """Show a scanning animation for files."""
    fake_files = [
        "auth/", "core/", "api/", "services/", "models/", "utils/",
        "handlers/", "middleware/", "config/", "security/", "permissions/",
    ]

    with Progress(
        SpinnerColumn(style=ROMEBOT_COLOR),
        TextColumn("[bold #EAB536]Rome-bot[/bold #EAB536] scanning"),
        BarColumn(bar_width=30, style="#EAB536", complete_style="#95D7E0"),
        TaskProgressColumn(),
        TextColumn("[dim]{task.description}[/dim]"),
        console=console,
        transient=True,
    ) as progress:
        task = progress.add_task(f"[cyan]{component}[/cyan]", total=files_count)

        for i in range(files_count):
            fake_path = f"src/{random.choice(fake_files)}{random.choice(['manager', 'handler', 'service', 'controller', 'utils'])}.py"
            progress.update(task, advance=1, description=fake_path)
            time.sleep(random.uniform(0.08, 0.18))


def simulate_upload_progress() -> None:
    """Simulate uploading evidence to Pretorin platform."""
    stages = [
        ("Validating artifact schema", 0.6),
        ("Encrypting payload", 0.5),
        ("Transmitting to Pretorin API", 0.8),
        ("Verifying receipt", 0.4),
    ]

    with Progress(
        SpinnerColumn(style="#95D7E0"),
        TextColumn("[#95D7E0]Uploading[/#95D7E0]"),
        BarColumn(bar_width=25, style="#95D7E0", complete_style="#EAB536"),
        TaskProgressColumn(),
        TextColumn("[dim]{task.description}[/dim]"),
        console=console,
        transient=True,
    ) as progress:
        task = progress.add_task("[cyan]AC-6[/cyan]", total=len(stages))

        for stage_name, duration in stages:
            progress.update(task, description=stage_name)
            time.sleep(duration)
            progress.advance(task)


def run_demo() -> None:
    """Run the JMCP compliance analysis demo."""
    console.clear()

    # Opening sequence
    rprint(MISSION_BANNER)
    time.sleep(1.0)

    rprint()
    rprint("[dim]Initializing secure environment...[/dim]")
    time.sleep(1.5)

    # System details panel
    rprint()
    system_info = f"""[bold]System:[/bold] {JMCP_SYSTEM['name']} ({JMCP_SYSTEM['short_name']})
[bold]Version:[/bold] {JMCP_SYSTEM['version']}
[bold]Classification:[/bold] [#FF6B6B]{JMCP_SYSTEM['classification']}[/#FF6B6B]
[bold]Sponsoring Agency:[/bold] {JMCP_SYSTEM['agency']}
[bold]Target Authorization:[/bold] [#00BFFF]{JMCP_SYSTEM['framework']}[/#00BFFF]"""

    rprint(Panel(
        system_info,
        title="[bold #00BFFF]Target System[/bold #00BFFF]",
        border_style="#00BFFF",
        padding=(1, 2),
    ))

    time.sleep(1.5)

    # Start analysis
    rprint()
    rprint("[#EAB536]━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/#EAB536]")
    rprint("[bold #EAB536]                    COMPLIANCE ANALYSIS INITIATED                      [/bold #EAB536]")
    rprint("[#EAB536]━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/#EAB536]")
    rprint()

    time.sleep(1.0)

    rprint(f"[#EAB536][°~°][/#EAB536] Analyzing [bold]{AC6_EVIDENCE['component']}[/bold] for [cyan]AC-6 (Least Privilege)[/cyan]...\n")

    time.sleep(1.0)

    # Scanning animation
    create_scanning_animation(AC6_EVIDENCE["files_scanned"], AC6_EVIDENCE["component"])

    time.sleep(0.5)
    rprint(f"\n[#95D7E0]✓[/#95D7E0] Scanned [bold]{AC6_EVIDENCE['files_scanned']}[/bold] files")
    time.sleep(0.8)
    rprint(f"[#FF6B6B]![/#FF6B6B] Found [bold]{AC6_EVIDENCE['evidence_found']}[/bold] findings requiring attention")

    time.sleep(1.5)

    # Show the finding
    finding = AC6_EVIDENCE["finding"]
    rprint()
    rprint(f"[bold #FF6B6B]Finding:[/bold #FF6B6B] {finding['description']}")
    time.sleep(0.5)
    rprint(f"[dim]Location:[/dim] [cyan]{finding['file']}:{finding['line']}[/cyan]")
    rprint()

    time.sleep(1.0)

    # Show code with syntax highlighting
    syntax = Syntax(
        finding["code"],
        "python",
        theme="monokai",
        line_numbers=True,
        start_line=finding["line"],
        word_wrap=True,
    )
    console.print(Panel(syntax, border_style="#FF6B6B", padding=(0, 1)))

    time.sleep(2.0)

    # Generate artifact
    rprint()
    rprint(f"[#EAB536][°◡°][/#EAB536] Generating compliance artifact...")
    time.sleep(1.2)

    # Show artifact summary
    artifact_summary = f"""[bold]Control:[/bold] AC-6 (Least Privilege)
[bold]Component:[/bold] {AC6_EVIDENCE['component']}
[bold]Status:[/bold] [#FF6B6B]PARTIAL - Excessive Privileges Detected[/#FF6B6B]
[bold]Confidence:[/bold] [#95D7E0]HIGH[/#95D7E0]
[bold]Evidence:[/bold] Service account 'svc_mission_backup' has admin role"""

    rprint(Panel(
        artifact_summary,
        title="[bold]Compliance Artifact[/bold]",
        border_style="#EAB536",
        padding=(0, 2),
    ))

    time.sleep(1.5)

    # Upload to platform
    rprint()
    rprint(f"[#EAB536][°~°][/#EAB536] Submitting evidence to Pretorin platform...")
    time.sleep(0.8)

    simulate_upload_progress()

    time.sleep(0.5)
    rprint(f"\n[#95D7E0]✓[/#95D7E0] Evidence submitted to Pretorin platform")

    time.sleep(1.0)

    # Final summary
    rprint()
    rprint("[#EAB536]━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/#EAB536]")
    rprint("[bold #EAB536]                        ANALYSIS COMPLETE                             [/bold #EAB536]")
    rprint("[#EAB536]━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/#EAB536]")
    rprint()

    time.sleep(0.8)

    rprint(Panel(
        f"""[bold]Control Assessed:[/bold] AC-6 (Least Privilege)
[bold]Result:[/bold] [#FF6B6B]Excessive privileges detected[/#FF6B6B]
[bold]Evidence Submitted:[/bold] [#95D7E0]Yes[/#95D7E0]

[dim]View findings and remediation guidance at:[/dim]
[link=https://platform.pretorin.com]https://platform.pretorin.com[/link]""",
        title="[bold #95D7E0]Summary[/bold #95D7E0]",
        border_style="#95D7E0",
        padding=(1, 2),
    ))

    time.sleep(1.0)

    rprint()
    rprint("[#EAB536][°◡°]/[/#EAB536] [bold #EAB536]Rome-bot says:[/bold #EAB536] \"Finding issues is the first step to compliance!\"")
    rprint()
