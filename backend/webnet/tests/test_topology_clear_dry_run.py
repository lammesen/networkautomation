import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from webnet.customers.models import Customer
from webnet.devices.models import Credential, Device, TopologyLink

User = get_user_model()


@pytest.mark.django_db
def test_topology_clear_dry_run_does_not_delete():
    customer = Customer.objects.create(name="Acme")
    user = User.objects.create_user(username="admin", password="secret123", role="admin")
    user.customers.add(customer)
    cred = Credential.objects.create(customer=customer, name="lab", username="u1")
    cred.password = "pass"
    cred.save()
    device = Device.objects.create(
        customer=customer,
        hostname="r1",
        mgmt_ip="192.0.2.10",
        vendor="cisco",
        platform="ios",
        credential=cred,
    )
    TopologyLink.objects.create(
        customer=customer,
        local_device=device,
        local_interface="Gi0/1",
        remote_hostname="sw-a",
        remote_interface="Gi0/2",
        protocol="cdp",
    )

    client = APIClient()
    client.login(username=user.username, password="secret123")

    resp = client.delete("/api/v1/topology/links/clear/?dry_run=true")
    assert resp.status_code == 200
    data = resp.json()
    assert data["deleted"] == 0
    assert data["would_delete"] == 1
    assert TopologyLink.objects.count() == 1
