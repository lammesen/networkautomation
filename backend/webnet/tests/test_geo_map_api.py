import pytest

from webnet.devices.models import Credential, Device, TopologyLink


@pytest.mark.django_db
def test_geo_map_returns_sites_and_links(api_client, admin_user, credential, customer):
    device_ny = Device.objects.create(
        customer=customer,
        hostname="ny-core",
        mgmt_ip="10.10.0.1",
        vendor="cisco",
        platform="ios",
        site="New York",
        site_latitude=40.7128,
        site_longitude=-74.0060,
        reachability_status="reachable",
        credential=credential,
    )
    device_lon = Device.objects.create(
        customer=customer,
        hostname="lon-core",
        mgmt_ip="10.20.0.1",
        vendor="cisco",
        platform="iosxe",
        site="London",
        site_latitude=51.5074,
        site_longitude=-0.1278,
        reachability_status="unreachable",
        credential=credential,
    )
    TopologyLink.objects.create(
        customer=customer,
        local_device=device_ny,
        local_interface="Gi0/0",
        remote_device=device_lon,
        remote_hostname="lon-core",
        remote_interface="Gi0/1",
        protocol="lldp",
    )

    api_client.force_authenticate(user=admin_user)
    resp = api_client.get("/api/v1/maps/geo")
    assert resp.status_code == 200
    payload = resp.json()

    site_names = {site["name"] for site in payload["sites"]}
    assert site_names == {"New York", "London"}

    ny = next(site for site in payload["sites"] if site["name"] == "New York")
    assert ny["device_count"] == 1
    assert ny["status"] == "healthy"

    lon = next(site for site in payload["sites"] if site["name"] == "London")
    assert lon["status"] == "down"
    assert lon["unreachable_devices"] == 1

    assert any(
        {edge["source_name"], edge["target_name"]} == {"New York", "London"}
        for edge in payload["links"]
    )


@pytest.mark.django_db
def test_geo_map_is_customer_scoped(api_client, viewer_user, credential, customer, other_customer):
    Device.objects.create(
        customer=customer,
        hostname="owned-device",
        mgmt_ip="10.30.0.1",
        vendor="juniper",
        platform="junos",
        site="Boston",
        site_latitude=42.3601,
        site_longitude=-71.0589,
        reachability_status="reachable",
        credential=credential,
    )
    other_cred = Credential(customer=other_customer, name="Other Cred", username="oth")
    other_cred.password = "pass123"
    other_cred.save()
    Device.objects.create(
        customer=other_customer,
        hostname="other-device",
        mgmt_ip="10.40.0.1",
        vendor="arista",
        platform="eos",
        site="Paris",
        site_latitude=48.8566,
        site_longitude=2.3522,
        reachability_status="reachable",
        credential=other_cred,
    )
    # Device without coordinates should be ignored
    Device.objects.create(
        customer=customer,
        hostname="no-coords",
        mgmt_ip="10.50.0.1",
        vendor="cisco",
        platform="ios",
        site="Chicago",
        credential=credential,
    )

    api_client.force_authenticate(user=viewer_user)
    resp = api_client.get("/api/v1/maps/geo")
    assert resp.status_code == 200
    payload = resp.json()

    site_names = {site["name"] for site in payload["sites"]}
    assert "Boston" in site_names
    assert "Paris" not in site_names
    assert "Chicago" not in site_names
