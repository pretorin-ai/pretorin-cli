"""Vendor management CLI commands for Pretorin."""

from __future__ import annotations

import asyncio
import os

import typer
from rich import print as rprint
from rich.console import Console
from rich.table import Table

from pretorin.cli.output import is_json_mode, print_json

console = Console()

app = typer.Typer(
    name="vendor",
    help="Vendor management and evidence linking.",
    no_args_is_help=True,
)

VALID_PROVIDER_TYPES = {"csp", "saas", "managed_service", "internal"}
VALID_ATTESTATION_TYPES = {"self_attested", "third_party_attestation", "vendor_provided"}


def _get_client():
    from pretorin.client import PretorianClient
    return PretorianClient()


@app.command("list")
def vendor_list():
    """List all vendors for the organization."""
    async def _run():
        client = _get_client()
        vendors = await client.list_vendors()
        if is_json_mode():
            print_json({"vendors": vendors, "total": len(vendors)})
            return
        if not vendors:
            rprint("[dim]No vendors found.[/dim]")
            return
        table = Table(title="Vendors")
        table.add_column("ID", style="dim")
        table.add_column("Name", style="bold")
        table.add_column("Type")
        table.add_column("Authorization")
        for v in vendors:
            table.add_row(
                str(v.get("id", "")),
                v.get("name", ""),
                v.get("provider_type", ""),
                v.get("authorization_level", ""),
            )
        console.print(table)
    asyncio.run(_run())


@app.command("create")
def vendor_create(
    name: str = typer.Argument(..., help="Vendor name"),
    provider_type: str = typer.Option(
        ..., "--type", "-t", help="Provider type: csp, saas, managed_service, internal"
    ),
    description: str = typer.Option(None, "--description", "-d", help="Vendor description"),
    authorization_level: str = typer.Option(
        None, "--authorization-level", "-a", help="Authorization level (e.g., 'FedRAMP High P-ATO')"
    ),
):
    """Create a new vendor entity."""
    if provider_type not in VALID_PROVIDER_TYPES:
        rprint(f"[red]Invalid provider type: {provider_type}. Must be one of: {', '.join(VALID_PROVIDER_TYPES)}[/red]")
        raise typer.Exit(1)

    async def _run():
        client = _get_client()
        result = await client.create_vendor(
            name=name,
            provider_type=provider_type,
            description=description,
            authorization_level=authorization_level,
        )
        if is_json_mode():
            print_json(result)
            return
        rprint(f"[green]Vendor created:[/green] {result.get('id', '')} - {result.get('name', '')}")
    asyncio.run(_run())


@app.command("get")
def vendor_get(vendor_id: str = typer.Argument(..., help="Vendor ID")):
    """Get vendor details."""
    async def _run():
        client = _get_client()
        result = await client.get_vendor(vendor_id)
        if is_json_mode():
            print_json(result)
            return
        rprint(f"[bold]{result.get('name', '')}[/bold]")
        rprint(f"  ID: {result.get('id', '')}")
        rprint(f"  Type: {result.get('provider_type', '')}")
        rprint(f"  Authorization: {result.get('authorization_level', 'N/A')}")
        if result.get("description"):
            rprint(f"  Description: {result['description']}")
    asyncio.run(_run())


@app.command("update")
def vendor_update(
    vendor_id: str = typer.Argument(..., help="Vendor ID"),
    name: str = typer.Option(None, "--name", help="New name"),
    description: str = typer.Option(None, "--description", "-d", help="New description"),
    provider_type: str = typer.Option(None, "--type", "-t", help="New provider type"),
    authorization_level: str = typer.Option(None, "--authorization-level", "-a", help="New authorization level"),
):
    """Update a vendor's fields."""
    fields = {}
    if name is not None:
        fields["name"] = name
    if description is not None:
        fields["description"] = description
    if provider_type is not None:
        if provider_type not in VALID_PROVIDER_TYPES:
            rprint(f"[red]Invalid provider type: {provider_type}[/red]")
            raise typer.Exit(1)
        fields["provider_type"] = provider_type
    if authorization_level is not None:
        fields["authorization_level"] = authorization_level

    if not fields:
        rprint("[yellow]No fields to update. Use --name, --description, --type, or --authorization-level.[/yellow]")
        raise typer.Exit(1)

    async def _run():
        client = _get_client()
        result = await client.update_vendor(vendor_id, **fields)
        if is_json_mode():
            print_json(result)
            return
        rprint(f"[green]Vendor updated:[/green] {result.get('name', '')}")
    asyncio.run(_run())


@app.command("delete")
def vendor_delete(
    vendor_id: str = typer.Argument(..., help="Vendor ID"),
    force: bool = typer.Option(False, "--force", "-f", help="Skip confirmation"),
):
    """Delete a vendor entity."""
    if not force:
        confirm = typer.confirm(f"Delete vendor {vendor_id}?")
        if not confirm:
            rprint("[dim]Cancelled.[/dim]")
            raise typer.Exit(0)

    async def _run():
        client = _get_client()
        await client.delete_vendor(vendor_id)
        rprint(f"[green]Vendor {vendor_id} deleted.[/green]")
    asyncio.run(_run())


@app.command("upload-doc")
def vendor_upload_doc(
    vendor_id: str = typer.Argument(..., help="Vendor ID"),
    file_path: str = typer.Argument(..., help="Local file path to upload"),
    name: str = typer.Option(None, "--name", "-n", help="Document display name"),
    description: str = typer.Option(None, "--description", "-d", help="Document description"),
    attestation_type: str = typer.Option(
        "vendor_provided", "--attestation-type", help="Attestation type: self_attested, third_party_attestation, vendor_provided"
    ),
):
    """Upload a vendor evidence document (SOC 2, CRM, FedRAMP package, etc)."""
    if not os.path.isfile(file_path):
        rprint(f"[red]File not found: {file_path}[/red]")
        raise typer.Exit(1)
    if attestation_type not in VALID_ATTESTATION_TYPES:
        rprint(f"[red]Invalid attestation type: {attestation_type}[/red]")
        raise typer.Exit(1)

    async def _run():
        client = _get_client()
        result = await client.upload_vendor_document(
            vendor_id=vendor_id,
            file_path=file_path,
            name=name,
            description=description,
            attestation_type=attestation_type,
        )
        if is_json_mode():
            print_json(result)
            return
        rprint(f"[green]Document uploaded:[/green] {result.get('id', '')} - {result.get('name', os.path.basename(file_path))}")
    asyncio.run(_run())


@app.command("list-docs")
def vendor_list_docs(vendor_id: str = typer.Argument(..., help="Vendor ID")):
    """List evidence documents linked to a vendor."""
    async def _run():
        client = _get_client()
        docs = await client.list_vendor_documents(vendor_id)
        if is_json_mode():
            print_json({"documents": docs, "total": len(docs)})
            return
        if not docs:
            rprint("[dim]No documents found for this vendor.[/dim]")
            return
        table = Table(title="Vendor Documents")
        table.add_column("ID", style="dim")
        table.add_column("Name", style="bold")
        table.add_column("Type")
        table.add_column("Attestation")
        for d in docs:
            table.add_row(
                str(d.get("id", "")),
                d.get("name", ""),
                d.get("evidence_type", ""),
                d.get("attestation_type", ""),
            )
        console.print(table)
    asyncio.run(_run())
