import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from webnet.customers.models import Customer
from webnet.devices.models import Credential, Device
from webnet.users.models import User
from webnet.compliance.models import CompliancePolicy, ComplianceResult
from webnet.jobs.models import Job


@pytest.mark.django_db
def test_compliance_htmx_lists():
    customer = Customer.objects.create(name="Acme")
    user = User.objects.create_user(username="dan", password="secret123", role="admin")
    user.customers.add(customer)
    cred = Credential.objects.create(customer=customer, name="lab", username="u1")
    cred.password = "pass"
    cred.save()
    device = Device.objects.create(
        customer=customer,
        hostname="router3",
        mgmt_ip="192.0.2.3",
        vendor="cisco",
        platform="ios",
        credential=cred,
    )
    policy = CompliancePolicy.objects.create(
        customer=customer,
        name="p1",
        description="",
        scope_json={"site": "lab"},
        definition_yaml="rules: []",
        created_by=user,
    )
    job = Job.objects.create(
        type="compliance_check", status="success", user=user, customer=customer
    )
    ComplianceResult.objects.create(
        policy=policy, device=device, job=job, status="pass", details_json={}
    )

    client = APIClient()
    client.login(username="dan", password="secret123")

    resp_policies = client.get(reverse("compliance-policies"), HTTP_HX_REQUEST="true")
    assert resp_policies.status_code == 200
    assert "p1" in resp_policies.content.decode()

    resp_results = client.get(reverse("compliance-results"), HTTP_HX_REQUEST="true")
    assert resp_results.status_code == 200
    body = resp_results.content.decode()
    assert "router3" in body
    assert "pass" in body
