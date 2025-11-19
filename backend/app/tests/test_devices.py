from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.core.security import create_access_token
from app.crud.device import create_device
from app.schemas.device import DeviceCreate

client = TestClient(app)


class TestDeviceRoutes:
    def setup_class(self):
        self.admin_headers = {"Authorization": f"Bearer {create_access_token(data={'sub': 'admin'})}"}
        self.operator_headers = {"Authorization": f"Bearer {create_access_token(data={'sub': 'operator'})}"}
        self.viewer_headers = {"Authorization": f"Bearer {create_access_token(data={'sub': 'viewer'})}"}

    def test_create_device(self, db: Session):
        device_data = {
            "hostname": "test-device-1",
            "mgmt_ip": "1.1.1.1",
            "vendor": "cisco",
            "platform": "ios",
        }
        response = client.post("/devices/", headers=self.operator_headers, json=device_data)
        assert response.status_code == 200
        data = response.json()
        assert data["hostname"] == device_data["hostname"]

    def test_read_devices(self, db: Session):
        create_device(db, DeviceCreate(hostname="test-device-2", mgmt_ip="2.2.2.2", vendor="juniper", platform="junos"))
        response = client.get("/devices/", headers=self.viewer_headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data) > 0

    def test_read_device(self, db: Session):
        device = create_device(db, DeviceCreate(hostname="test-device-3", mgmt_ip="3.3.3.3", vendor="arista", platform="eos"))
        response = client.get(f"/devices/{device.id}", headers=self.viewer_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == device.id

    def test_update_device(self, db: Session):
        device = create_device(db, DeviceCreate(hostname="test-device-4", mgmt_ip="4.4.4.4", vendor="cisco", platform="ios"))
        update_data = {"role": "core"}
        response = client.put(f"/devices/{device.id}", headers=self.operator_headers, json=update_data)
        assert response.status_code == 200
        data = response.json()
        assert data["role"] == "core"

    def test_delete_device(self, db: Session):
        device = create_device(db, DeviceCreate(hostname="test-device-5", mgmt_ip="5.5.5.5", vendor="cisco", platform="ios"))
        response = client.delete(f"/devices/{device.id}", headers=self.admin_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["enabled"] is False
