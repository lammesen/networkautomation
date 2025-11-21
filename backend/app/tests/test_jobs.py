"""Tests for job endpoints."""

from app.db.models import Job


def test_list_jobs(client, auth_headers, admin_user, db_session, test_customer):
    """Test listing jobs."""
    # Create a test job
    job = Job(
        type="run_commands",
        status="queued",
        user_id=admin_user.id,
        customer_id=test_customer.id,
    )
    db_session.add(job)
    db_session.commit()
    
    response = client.get("/api/v1/jobs", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 1


def test_get_job(client, auth_headers, admin_user, db_session, test_customer):
    """Test getting a specific job."""
    job = Job(
        type="run_commands",
        status="queued",
        user_id=admin_user.id,
        customer_id=test_customer.id,
    )
    db_session.add(job)
    db_session.commit()
    db_session.refresh(job)
    
    response = client.get(f"/api/v1/jobs/{job.id}", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["type"] == "run_commands"
    assert data["status"] == "queued"


def test_get_job_logs(client, auth_headers, admin_user, db_session, test_customer):
    """Test getting job logs."""
    job = Job(
        type="run_commands",
        status="running",
        user_id=admin_user.id,
        customer_id=test_customer.id,
    )
    db_session.add(job)
    db_session.commit()
    db_session.refresh(job)
    
    response = client.get(f"/api/v1/jobs/{job.id}/logs", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)


def test_get_job_results(client, auth_headers, admin_user, db_session, test_customer):
    """Test getting job results."""
    job = Job(
        type="run_commands",
        status="success",
        user_id=admin_user.id,
        customer_id=test_customer.id,
        result_summary_json={"total": 1, "success": 1, "failed": 0},
    )
    db_session.add(job)
    db_session.commit()
    db_session.refresh(job)
    
    response = client.get(f"/api/v1/jobs/{job.id}/results", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["job_id"] == job.id
    assert "results" in data


def test_filter_jobs_by_status(client, auth_headers, admin_user, db_session, test_customer):
    """Test filtering jobs by status."""
    job1 = Job(
        type="run_commands",
        status="queued",
        user_id=admin_user.id,
        customer_id=test_customer.id,
    )
    job2 = Job(
        type="config_backup",
        status="running",
        user_id=admin_user.id,
        customer_id=test_customer.id,
    )
    db_session.add(job1)
    db_session.add(job2)
    db_session.commit()
    
    response = client.get("/api/v1/jobs?status=queued", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert all(job["status"] == "queued" for job in data)


def test_filter_jobs_by_type(client, auth_headers, admin_user, db_session, test_customer):
    """Test filtering jobs by type."""
    job1 = Job(
        type="run_commands",
        status="queued",
        user_id=admin_user.id,
        customer_id=test_customer.id,
    )
    job2 = Job(
        type="config_backup",
        status="queued",
        user_id=admin_user.id,
        customer_id=test_customer.id,
    )
    db_session.add(job1)
    db_session.add(job2)
    db_session.commit()
    
    response = client.get("/api/v1/jobs?type=run_commands", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert all(job["type"] == "run_commands" for job in data)
