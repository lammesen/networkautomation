"""Tests for CDP/LLDP discovery parsing and DiscoveredDevice functionality."""

import pytest
from django.contrib.auth import get_user_model

from webnet.jobs.models import Job
from webnet.jobs import tasks
from webnet.customers.models import Customer
from webnet.devices.models import Device, Credential, TopologyLink, DiscoveredDevice

User = get_user_model()


# Sample CDP output (Cisco)
CDP_OUTPUT = """
Device ID: switch01.example.com
Entry address(es):
  IP address: 192.168.1.1
Platform: Cisco IOS Software, C3750 Software
Interface: GigabitEthernet0/1, Port ID (outgoing port): GigabitEthernet0/24
Holdtime : 155 sec

Device ID: router01
Entry address(es):
  IP address: 192.168.1.254
Platform: Cisco IOS XE
Interface: GigabitEthernet0/2, Port ID (outgoing port): GigabitEthernet1/0/1
Holdtime : 140 sec
"""

# Sample LLDP output (Cisco IOS)
LLDP_OUTPUT_CISCO = """
----------------------------------------
Local Intf: Gi0/1
Chassis id: switch02.example.com
Port id: Gi0/24
Port Description: GigabitEthernet0/24
System Name: switch02.example.com

System Description:
Cisco IOS Software, C2960 Software

Time remaining: 101 seconds
System Capabilities: B,R
Enabled Capabilities: B,R

Management Addresses:
    IP: 10.1.1.2

----------------------------------------
Local Intf: Gi0/2
Chassis id: 00:11:22:33:44:55
Port id: eth0
Port Description: Ethernet0
System Name: linuxhost01

System Description:
Linux 5.4.0

Management Addresses:
    IP: 10.1.1.100

----------------------------------------
"""

# Sample LLDP output (Juniper)
LLDP_OUTPUT_JUNIPER = """
Local Interface    : ge-0/0/0
Parent Interface   : -
Chassis Id         : 00:aa:bb:cc:dd:ee
Port id            : ge-0/0/1
Port description   : to-core-sw
System Name        : core-switch

Local Interface    : ge-0/0/1
Parent Interface   : -
Chassis Id         : 00:11:22:33:44:55
Port id            : Ethernet1
Port description   : uplink
System Name        : access-sw01
"""


class TestCDPParsing:
    """Tests for CDP neighbor parsing."""

    def test_parse_cdp_neighbors_basic(self):
        """Test basic CDP parsing."""
        neighbors = tasks._parse_cdp_neighbors(CDP_OUTPUT)
        assert len(neighbors) == 2

    def test_parse_cdp_neighbors_extracts_hostname(self):
        """Test CDP parsing extracts hostname correctly."""
        neighbors = tasks._parse_cdp_neighbors(CDP_OUTPUT)
        hostnames = [n["remote_hostname"] for n in neighbors]
        assert "switch01.example.com" in hostnames
        assert "router01" in hostnames

    def test_parse_cdp_neighbors_extracts_interfaces(self):
        """Test CDP parsing extracts interface names."""
        neighbors = tasks._parse_cdp_neighbors(CDP_OUTPUT)
        n = next(n for n in neighbors if n["remote_hostname"] == "switch01.example.com")
        assert n["local_interface"] == "GigabitEthernet0/1"
        assert n["remote_interface"] == "GigabitEthernet0/24"

    def test_parse_cdp_neighbors_extracts_ip(self):
        """Test CDP parsing extracts management IP."""
        neighbors = tasks._parse_cdp_neighbors(CDP_OUTPUT)
        n = next(n for n in neighbors if n["remote_hostname"] == "switch01.example.com")
        assert n["remote_ip"] == "192.168.1.1"

    def test_parse_cdp_neighbors_extracts_platform(self):
        """Test CDP parsing extracts platform info."""
        neighbors = tasks._parse_cdp_neighbors(CDP_OUTPUT)
        n = next(n for n in neighbors if n["remote_hostname"] == "switch01.example.com")
        assert n["remote_platform"] is not None
        assert "Cisco" in n["remote_platform"]

    def test_parse_cdp_neighbors_empty_input(self):
        """Test CDP parsing handles empty input."""
        neighbors = tasks._parse_cdp_neighbors("")
        assert neighbors == []

    def test_parse_cdp_neighbors_none_input(self):
        """Test CDP parsing handles None-ish input."""
        neighbors = tasks._parse_cdp_neighbors(None)  # type: ignore
        assert neighbors == []


class TestLLDPParsing:
    """Tests for LLDP neighbor parsing."""

    def test_parse_lldp_neighbors_cisco(self):
        """Test LLDP parsing for Cisco IOS format."""
        neighbors = tasks._parse_lldp_neighbors(LLDP_OUTPUT_CISCO)
        assert len(neighbors) >= 2

    def test_parse_lldp_neighbors_extracts_hostname(self):
        """Test LLDP parsing extracts hostname from System Name."""
        neighbors = tasks._parse_lldp_neighbors(LLDP_OUTPUT_CISCO)
        hostnames = [n["remote_hostname"] for n in neighbors]
        assert "switch02.example.com" in hostnames

    def test_parse_lldp_neighbors_extracts_interfaces(self):
        """Test LLDP parsing extracts interface names."""
        neighbors = tasks._parse_lldp_neighbors(LLDP_OUTPUT_CISCO)
        n = next(n for n in neighbors if n["remote_hostname"] == "switch02.example.com")
        assert n["local_interface"] == "Gi0/1"

    def test_parse_lldp_neighbors_extracts_ip(self):
        """Test LLDP parsing extracts management IP."""
        neighbors = tasks._parse_lldp_neighbors(LLDP_OUTPUT_CISCO)
        n = next(n for n in neighbors if n["remote_hostname"] == "switch02.example.com")
        assert n["remote_ip"] == "10.1.1.2"

    def test_parse_lldp_neighbors_prefers_port_description(self):
        """Test LLDP parsing prefers Port Description over Port ID."""
        neighbors = tasks._parse_lldp_neighbors(LLDP_OUTPUT_CISCO)
        n = next(n for n in neighbors if n["remote_hostname"] == "switch02.example.com")
        assert n["remote_interface"] == "GigabitEthernet0/24"

    def test_parse_lldp_neighbors_juniper(self):
        """Test LLDP parsing for Juniper format."""
        neighbors = tasks._parse_lldp_neighbors(LLDP_OUTPUT_JUNIPER)
        assert len(neighbors) >= 2
        hostnames = [n["remote_hostname"] for n in neighbors]
        assert "core-switch" in hostnames
        assert "access-sw01" in hostnames

    def test_parse_lldp_neighbors_empty_input(self):
        """Test LLDP parsing handles empty input."""
        neighbors = tasks._parse_lldp_neighbors("")
        assert neighbors == []


class _FakeResult:
    def __init__(self, output: str, failed: bool = False):
        self.failed = failed
        self.result = output
        self.exception = None


class _FakeNR:
    def __init__(self, cdp_output: str = "", lldp_output: str = ""):
        self.cdp_output = cdp_output
        self.lldp_output = lldp_output

    def run(self, task, **kwargs):
        cmd = kwargs.get("command_string", "")
        if "cdp" in cmd:
            return {"h1": _FakeResult(self.cdp_output)}
        elif "lldp" in cmd:
            return {"h1": _FakeResult(self.lldp_output)}
        return {"h1": _FakeResult("")}


class _FakeInventory:
    def __init__(self, hosts_present: bool = True):
        self.hosts = {"h1": {}} if hosts_present else {}


@pytest.mark.django_db
class TestTopologyDiscoveryJob:
    """Tests for topology_discovery_job task."""

    @pytest.fixture
    def setup_customer_and_device(self):
        """Create a customer with credentials and device."""
        customer = Customer.objects.create(name="TestCo")
        user = User.objects.create_user(username="tester", password="secret123", role="admin")
        user.customers.add(customer)
        cred = Credential.objects.create(customer=customer, name="lab", username="u1")
        cred.password = "pass"
        cred.save()
        device = Device.objects.create(
            customer=customer,
            hostname="h1",
            mgmt_ip="192.0.2.10",
            vendor="cisco",
            platform="ios",
            credential=cred,
        )
        return customer, user, device, cred

    def test_discovery_creates_topology_links(self, monkeypatch, setup_customer_and_device):
        """Test that discovery creates TopologyLink records."""
        customer, user, device, cred = setup_customer_and_device
        job = Job.objects.create(
            type="topology_discovery", status="queued", user=user, customer=customer
        )

        monkeypatch.setattr(tasks, "build_inventory", lambda targets, customer_id: _FakeInventory())
        monkeypatch.setattr(
            tasks,
            "_nr_from_inventory",
            lambda inv: _FakeNR(cdp_output=CDP_OUTPUT),
        )

        tasks.topology_discovery_job(job.id, targets={}, protocol="cdp")

        links = TopologyLink.objects.filter(customer=customer)
        assert links.count() >= 1
        job.refresh_from_db()
        assert job.status == "success"

    def test_discovery_lldp_protocol(self, monkeypatch, setup_customer_and_device):
        """Test LLDP-only discovery."""
        customer, user, device, cred = setup_customer_and_device
        job = Job.objects.create(
            type="topology_discovery", status="queued", user=user, customer=customer
        )

        monkeypatch.setattr(tasks, "build_inventory", lambda targets, customer_id: _FakeInventory())
        monkeypatch.setattr(
            tasks,
            "_nr_from_inventory",
            lambda inv: _FakeNR(lldp_output=LLDP_OUTPUT_CISCO),
        )

        tasks.topology_discovery_job(job.id, targets={}, protocol="lldp")

        links = TopologyLink.objects.filter(customer=customer, protocol="lldp")
        assert links.count() >= 1

    def test_discovery_both_protocols(self, monkeypatch, setup_customer_and_device):
        """Test discovery with both CDP and LLDP."""
        customer, user, device, cred = setup_customer_and_device
        job = Job.objects.create(
            type="topology_discovery", status="queued", user=user, customer=customer
        )

        monkeypatch.setattr(tasks, "build_inventory", lambda targets, customer_id: _FakeInventory())
        monkeypatch.setattr(
            tasks,
            "_nr_from_inventory",
            lambda inv: _FakeNR(cdp_output=CDP_OUTPUT, lldp_output=LLDP_OUTPUT_CISCO),
        )

        tasks.topology_discovery_job(job.id, targets={}, protocol="both")

        cdp_links = TopologyLink.objects.filter(customer=customer, protocol="cdp")
        lldp_links = TopologyLink.objects.filter(customer=customer, protocol="lldp")
        assert cdp_links.count() >= 1
        assert lldp_links.count() >= 1

    def test_auto_create_discovered_devices(self, monkeypatch, setup_customer_and_device):
        """Test auto_create_devices creates DiscoveredDevice entries."""
        customer, user, device, cred = setup_customer_and_device
        job = Job.objects.create(
            type="topology_discovery", status="queued", user=user, customer=customer
        )

        monkeypatch.setattr(tasks, "build_inventory", lambda targets, customer_id: _FakeInventory())
        monkeypatch.setattr(
            tasks,
            "_nr_from_inventory",
            lambda inv: _FakeNR(cdp_output=CDP_OUTPUT),
        )

        tasks.topology_discovery_job(job.id, targets={}, protocol="cdp", auto_create_devices=True)

        discovered = DiscoveredDevice.objects.filter(customer=customer)
        assert discovered.count() >= 1
        assert discovered.filter(hostname="switch01.example.com").exists()
        assert discovered.first().status == DiscoveredDevice.STATUS_PENDING


@pytest.mark.django_db
class TestDiscoveredDeviceModel:
    """Tests for DiscoveredDevice model."""

    @pytest.fixture
    def setup_discovered_device(self):
        """Create a customer and discovered device."""
        customer = Customer.objects.create(name="TestCo")
        user = User.objects.create_user(username="reviewer", password="secret123", role="admin")
        user.customers.add(customer)
        cred = Credential.objects.create(customer=customer, name="lab", username="u1")
        cred.password = "pass"
        cred.save()

        discovered = DiscoveredDevice.objects.create(
            customer=customer,
            hostname="new-switch",
            mgmt_ip="10.0.0.1",
            platform="Cisco IOS",
            discovered_via_protocol="lldp",
        )
        return customer, user, discovered, cred

    def test_approve_creates_device(self, setup_discovered_device):
        """Test approving a discovered device creates a Device."""
        customer, user, discovered, cred = setup_discovered_device

        device = discovered.approve_and_create_device(
            credential=cred,
            user=user,
            vendor="cisco",
        )

        assert device.hostname == "new-switch"
        assert device.mgmt_ip == "10.0.0.1"
        assert device.customer == customer
        assert device.credential == cred

        discovered.refresh_from_db()
        assert discovered.status == DiscoveredDevice.STATUS_APPROVED
        assert discovered.reviewed_by == user
        assert discovered.created_device == device

    def test_approve_requires_vendor(self, setup_discovered_device):
        """Test approving without vendor raises error."""
        customer, user, discovered, cred = setup_discovered_device

        with pytest.raises(ValueError, match="Vendor is required"):
            discovered.approve_and_create_device(credential=cred, user=user)

    def test_reject_sets_status(self, setup_discovered_device):
        """Test rejecting sets status correctly."""
        customer, user, discovered, cred = setup_discovered_device

        discovered.reject(user=user, notes="Not a managed device")

        discovered.refresh_from_db()
        assert discovered.status == DiscoveredDevice.STATUS_REJECTED
        assert discovered.reviewed_by == user
        assert discovered.notes == "Not a managed device"

    def test_ignore_sets_status(self, setup_discovered_device):
        """Test ignoring sets status correctly."""
        customer, user, discovered, cred = setup_discovered_device

        discovered.ignore(user=user, notes="Host server, not network device")

        discovered.refresh_from_db()
        assert discovered.status == DiscoveredDevice.STATUS_IGNORED


@pytest.mark.django_db
class TestDiscoveredDeviceAPI:
    """Tests for DiscoveredDevice API endpoints."""

    @pytest.fixture
    def api_client_with_auth(self):
        """Create authenticated test client."""
        from rest_framework.test import APIClient
        from rest_framework_simplejwt.tokens import RefreshToken

        customer = Customer.objects.create(name="APICo")
        user = User.objects.create_user(username="api_user", password="secret123", role="admin")
        user.customers.add(customer)
        cred = Credential.objects.create(customer=customer, name="default", username="u1")
        cred.password = "pass"
        cred.save()

        client = APIClient()
        refresh = RefreshToken.for_user(user)
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")

        return client, customer, user, cred

    def test_list_discovered_devices(self, api_client_with_auth):
        """Test listing discovered devices."""
        client, customer, user, cred = api_client_with_auth

        DiscoveredDevice.objects.create(
            customer=customer, hostname="discovered1", discovered_via_protocol="cdp"
        )
        DiscoveredDevice.objects.create(
            customer=customer, hostname="discovered2", discovered_via_protocol="lldp"
        )

        response = client.get("/api/v1/topology/discovered-devices/", {"customer_id": customer.id})
        assert response.status_code == 200
        data = response.json()
        # Handle both paginated and non-paginated responses
        results = data.get("results", data)
        assert len(results) >= 2

    def test_approve_discovered_device(self, api_client_with_auth):
        """Test approving a discovered device via API."""
        client, customer, user, cred = api_client_with_auth

        discovered = DiscoveredDevice.objects.create(
            customer=customer,
            hostname="pending-device",
            mgmt_ip="10.0.0.5",
            discovered_via_protocol="cdp",
        )

        response = client.post(
            f"/api/v1/topology/discovered-devices/{discovered.id}/approve/",
            {"credential_id": cred.id, "vendor": "cisco"},
            format="json",
        )

        assert response.status_code == 201
        assert "device_id" in response.json()

        discovered.refresh_from_db()
        assert discovered.status == DiscoveredDevice.STATUS_APPROVED

    def test_reject_discovered_device(self, api_client_with_auth):
        """Test rejecting a discovered device via API."""
        client, customer, user, cred = api_client_with_auth

        discovered = DiscoveredDevice.objects.create(
            customer=customer, hostname="reject-me", discovered_via_protocol="lldp"
        )

        response = client.post(
            f"/api/v1/topology/discovered-devices/{discovered.id}/reject/",
            {"notes": "Not needed"},
            format="json",
        )

        assert response.status_code == 200
        discovered.refresh_from_db()
        assert discovered.status == DiscoveredDevice.STATUS_REJECTED

    def test_stats_endpoint(self, api_client_with_auth):
        """Test discovery queue stats endpoint."""
        client, customer, user, cred = api_client_with_auth

        DiscoveredDevice.objects.create(
            customer=customer, hostname="p1", status=DiscoveredDevice.STATUS_PENDING
        )
        DiscoveredDevice.objects.create(
            customer=customer, hostname="p2", status=DiscoveredDevice.STATUS_PENDING
        )
        DiscoveredDevice.objects.create(
            customer=customer, hostname="a1", status=DiscoveredDevice.STATUS_APPROVED
        )

        response = client.get(
            "/api/v1/topology/discovered-devices/stats/", {"customer_id": customer.id}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["pending"] == 2
        assert data["approved"] == 1
        assert data["total"] == 3

    def test_bulk_approve(self, api_client_with_auth):
        """Test bulk approve endpoint."""
        client, customer, user, cred = api_client_with_auth

        d1 = DiscoveredDevice.objects.create(
            customer=customer, hostname="bulk1", mgmt_ip="10.0.0.1"
        )
        d2 = DiscoveredDevice.objects.create(
            customer=customer, hostname="bulk2", mgmt_ip="10.0.0.2"
        )

        response = client.post(
            "/api/v1/topology/discovered-devices/bulk-approve/",
            {"ids": [d1.id, d2.id], "credential_id": cred.id, "vendor": "cisco"},
            format="json",
        )

        assert response.status_code == 201
        assert len(response.json()["created"]) == 2

        d1.refresh_from_db()
        d2.refresh_from_db()
        assert d1.status == DiscoveredDevice.STATUS_APPROVED
        assert d2.status == DiscoveredDevice.STATUS_APPROVED
