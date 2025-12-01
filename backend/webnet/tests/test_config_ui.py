import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from webnet.customers.models import Customer
from webnet.devices.models import Credential, Device
from webnet.config_mgmt.models import ConfigSnapshot
from webnet.users.models import User


@pytest.mark.django_db
def test_config_snapshots_htmx_list():
    customer = Customer.objects.create(name="Acme")
    user = User.objects.create_user(username="cathy", password="secret123", role="admin")
    user.customers.add(customer)
    cred = Credential.objects.create(customer=customer, name="lab", username="u1")
    cred.password = "pass"
    cred.save()
    device = Device.objects.create(
        customer=customer,
        hostname="router2",
        mgmt_ip="192.0.2.2",
        vendor="cisco",
        platform="ios",
        credential=cred,
    )
    ConfigSnapshot.objects.create(
        device=device, source="manual", config_text="version 1", hash="abc"
    )

    client = APIClient()
    client.login(username="cathy", password="secret123")
    url = reverse("config-list")
    resp = client.get(url, HTTP_HX_REQUEST="true")
    assert resp.status_code == 200
    body = resp.content.decode()
    assert "router2" in body
    assert "abc" in body


@pytest.mark.django_db
def test_config_diff_view():
    customer = Customer.objects.create(name="Acme")
    user = User.objects.create_user(username="cathy", password="secret123", role="admin")
    user.customers.add(customer)
    cred = Credential.objects.create(customer=customer, name="lab", username="u1")
    cred.password = "pass"
    cred.save()
    device = Device.objects.create(
        customer=customer,
        hostname="router2",
        mgmt_ip="192.0.2.2",
        vendor="cisco",
        platform="ios",
        credential=cred,
    )
    snap1 = ConfigSnapshot.objects.create(
        device=device, source="manual", config_text="line1\nline2", hash="h1"
    )
    snap2 = ConfigSnapshot.objects.create(
        device=device, source="manual", config_text="line1\nline3", hash="h2"
    )
    client = APIClient()
    client.login(username="cathy", password="secret123")
    url = reverse("config-diff") + f"?from={snap1.id}&to={snap2.id}"
    resp = client.get(url)
    assert resp.status_code == 200
    assert "line2" in resp.content.decode()
