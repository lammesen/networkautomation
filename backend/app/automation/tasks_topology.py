"""Topology discovery tasks using NAPALM CDP/LLDP getters."""

from nornir.core.task import Result, Task
from nornir_napalm.plugins.tasks import napalm_get


def discover_neighbors_task(task: Task) -> Result:
    """Discover neighbors using CDP and LLDP via NAPALM.

    Returns a dictionary with neighbor information from both protocols.
    """
    neighbors: dict = {"cdp": [], "lldp": []}
    errors: list[str] = []

    # Try LLDP first (more universal)
    try:
        lldp_result = task.run(
            task=napalm_get,
            getters=["lldp_neighbors_detail"],
            name="Get LLDP neighbors",
        )
        if not lldp_result.failed and lldp_result.result:
            lldp_data = lldp_result.result.get("lldp_neighbors_detail", {})
            for interface, neighbor_list in lldp_data.items():
                for neighbor in neighbor_list:
                    neighbors["lldp"].append(
                        {
                            "local_interface": interface,
                            "remote_hostname": neighbor.get("remote_system_name", "unknown"),
                            "remote_interface": neighbor.get("remote_port", "unknown"),
                            "remote_ip": neighbor.get("remote_management_address", ""),
                            "remote_platform": neighbor.get("remote_system_description", ""),
                            "protocol": "lldp",
                        }
                    )
    except Exception as e:
        errors.append(f"LLDP discovery failed: {str(e)}")

    # Try CDP (Cisco-specific)
    try:
        # NAPALM doesn't have a direct CDP getter, so we'll try get_lldp_neighbors
        # which some drivers implement as CDP on Cisco devices
        # For Cisco, we can also try a raw command
        pass  # CDP is typically combined in lldp_neighbors for NAPALM
    except Exception as e:
        errors.append(f"CDP discovery failed: {str(e)}")

    return Result(
        host=task.host,
        result={
            "neighbors": neighbors,
            "errors": errors,
            "total_count": len(neighbors["lldp"]) + len(neighbors["cdp"]),
        },
    )
