"""Topology API endpoints for network discovery and visualization."""

from fastapi import APIRouter, Depends, Query

from app.celery_app import celery_app
from app.db import TopologyLink, Device, get_db
from app.dependencies import get_job_service, get_operator_context, get_tenant_context
from app.domain.context import TenantRequestContext
from app.services.job_service import JobService
from sqlalchemy.orm import Session

router = APIRouter(prefix="/topology", tags=["topology"])


@router.post("/discover", status_code=202)
def trigger_topology_discovery(
    targets: dict = {},
    service: JobService = Depends(get_job_service),
    context: TenantRequestContext = Depends(get_operator_context),
) -> dict:
    """Trigger topology discovery for devices matching the filters.

    Uses LLDP to discover neighbors and build the network topology.
    """
    job = service.create_job(
        job_type="topology_discovery",
        user=context.user,
        customer_id=context.customer_id,
        target_summary={"filters": targets},
        payload={},
    )

    celery_app.send_task(
        "topology_discovery_job",
        args=[job.id, targets],
    )

    return {"job_id": job.id, "status": "queued"}


@router.get("/links")
def list_topology_links(
    device_id: int | None = Query(None, description="Filter by device ID"),
    db: Session = Depends(get_db),
    context: TenantRequestContext = Depends(get_tenant_context),
) -> list[dict]:
    """List discovered topology links for the current customer."""
    query = db.query(TopologyLink).filter(TopologyLink.customer_id == context.customer_id)

    if device_id:
        query = query.filter(
            (TopologyLink.local_device_id == device_id)
            | (TopologyLink.remote_device_id == device_id)
        )

    links = query.order_by(TopologyLink.discovered_at.desc()).all()

    return [
        {
            "id": link.id,
            "local_device_id": link.local_device_id,
            "local_device_hostname": link.local_device.hostname if link.local_device else None,
            "local_interface": link.local_interface,
            "remote_device_id": link.remote_device_id,
            "remote_device_hostname": (
                link.remote_device.hostname if link.remote_device else link.remote_hostname
            ),
            "remote_interface": link.remote_interface,
            "remote_ip": link.remote_ip,
            "remote_platform": link.remote_platform,
            "protocol": link.protocol,
            "discovered_at": link.discovered_at.isoformat(),
            "is_known_device": link.remote_device_id is not None,
        }
        for link in links
    ]


@router.get("/graph")
def get_topology_graph(
    db: Session = Depends(get_db),
    context: TenantRequestContext = Depends(get_tenant_context),
) -> dict:
    """Get topology data formatted for graph visualization.

    Returns nodes (devices) and edges (links) suitable for rendering
    with visualization libraries like React Flow or D3.js.
    """
    # Get all devices for this customer
    devices = (
        db.query(Device)
        .filter(Device.customer_id == context.customer_id, Device.enabled.is_(True))
        .all()
    )

    # Get all links for this customer
    links = db.query(TopologyLink).filter(TopologyLink.customer_id == context.customer_id).all()

    # Build nodes from devices
    nodes = [
        {
            "id": str(device.id),
            "label": device.hostname,
            "data": {
                "hostname": device.hostname,
                "mgmt_ip": device.mgmt_ip,
                "vendor": device.vendor,
                "platform": device.platform,
                "role": device.role,
                "site": device.site,
                "reachability": device.reachability_status,
            },
            "type": "device",
        }
        for device in devices
    ]

    # Track unknown neighbors to add as nodes
    unknown_neighbors: dict[str, dict] = {}

    # Build edges from links
    edges = []
    for link in links:
        source = str(link.local_device_id)
        target = (
            str(link.remote_device_id)
            if link.remote_device_id
            else f"unknown_{link.remote_hostname}"
        )

        # If remote device is unknown, add it as a node
        if not link.remote_device_id:
            unknown_key = f"unknown_{link.remote_hostname}"
            if unknown_key not in unknown_neighbors:
                unknown_neighbors[unknown_key] = {
                    "id": unknown_key,
                    "label": link.remote_hostname,
                    "data": {
                        "hostname": link.remote_hostname,
                        "mgmt_ip": link.remote_ip or "",
                        "platform": link.remote_platform or "",
                        "is_unknown": True,
                    },
                    "type": "unknown_device",
                }

        edges.append(
            {
                "id": f"link_{link.id}",
                "source": source,
                "target": target,
                "data": {
                    "local_interface": link.local_interface,
                    "remote_interface": link.remote_interface,
                    "protocol": link.protocol,
                    "discovered_at": link.discovered_at.isoformat(),
                },
            }
        )

    # Add unknown neighbors as nodes
    nodes.extend(unknown_neighbors.values())

    return {
        "nodes": nodes,
        "edges": edges,
        "stats": {
            "known_devices": len(devices),
            "unknown_devices": len(unknown_neighbors),
            "total_links": len(links),
        },
    }


@router.delete("/links")
def clear_topology_links(
    db: Session = Depends(get_db),
    context: TenantRequestContext = Depends(get_operator_context),
) -> dict:
    """Clear all topology links for the current customer.

    Useful before running a fresh discovery.
    """
    deleted = (
        db.query(TopologyLink).filter(TopologyLink.customer_id == context.customer_id).delete()
    )
    db.commit()

    return {"deleted": deleted}
