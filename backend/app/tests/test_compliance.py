from __future__ import annotations

from datetime import timedelta

from app.compliance.models import CompliancePolicy, ComplianceResult
from app.core.time import utcnow
from app.devices.models import Device
from app.jobs.models import Job


def test_compliance_policy_crud(client):
    create_payload = {
        "name": "edge-bgp",
        "scope": {"roles": ["edge"]},
        "definition": {"bgp_neighbors": {"peers": []}},
    }
    create_resp = client.post("/api/compliance/policies", json=create_payload)
    assert create_resp.status_code == 200
    policy_id = create_resp.json()["id"]

    list_resp = client.get("/api/compliance/policies")
    assert list_resp.status_code == 200
    policies = list_resp.json()
    assert any(p["name"] == "edge-bgp" for p in policies)

    update_resp = client.put(
        f"/api/compliance/policies/{policy_id}", json={"name": "core-bgp"}
    )
    assert update_resp.status_code == 200
    assert update_resp.json()["name"] == "core-bgp"

    delete_resp = client.delete(f"/api/compliance/policies/{policy_id}")
    assert delete_resp.status_code == 204
    final_list = client.get("/api/compliance/policies").json()
    assert final_list == []


def test_device_compliance_summary(client, db_session):
    policy = CompliancePolicy(
        name="baseline",
        scope_json="{}",
        definition_yaml="interfaces: {}",
        created_by=1,
    )
    device = Device(hostname="r1", mgmt_ip="10.0.0.1")
    job = Job(type="compliance", status="success", user_id=1)
    db_session.add_all([policy, device, job])
    db_session.commit()

    earlier = utcnow() - timedelta(minutes=5)
    db_session.add(
        ComplianceResult(
            policy_id=policy.id,
            device_id=device.id,
            job_id=job.id,
            ts=earlier,
            status="fail",
            details_json="{}",
        )
    )
    db_session.add(
        ComplianceResult(
            policy_id=policy.id,
            device_id=device.id,
            job_id=job.id,
            status="pass",
            details_json="{}",
        )
    )
    db_session.commit()

    summary_resp = client.get(f"/api/compliance/devices/{device.id}")
    assert summary_resp.status_code == 200
    summary = summary_resp.json()
    assert summary[str(policy.id)] == "pass"
