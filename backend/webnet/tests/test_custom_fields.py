"""Tests for custom fields functionality."""

import pytest
from rest_framework.test import APIClient

from webnet.customers.models import Customer
from webnet.users.models import User
from webnet.devices.models import Device, Credential
from webnet.core.models import CustomFieldDefinition


@pytest.mark.django_db
class TestCustomFieldDefinitionAPI:
    """Tests for CustomFieldDefinition API."""

    def test_create_custom_field_definition(self):
        """Test creating a custom field definition."""
        customer = Customer.objects.create(name="Test Corp")
        user = User.objects.create_user(username="admin", password="password", role="admin")
        user.customers.add(customer)

        client = APIClient()
        client.force_authenticate(user=user)

        data = {
            "customer": customer.id,
            "name": "asset_tag",
            "label": "Asset Tag",
            "model_type": "device",
            "field_type": "text",
            "description": "Physical asset tag number",
            "required": False,
            "weight": 100,
            "is_active": True,
        }

        response = client.post("/api/v1/custom-fields/", data, format="json")
        assert response.status_code == 201
        assert response.data["name"] == "asset_tag"
        assert response.data["label"] == "Asset Tag"
        assert response.data["model_type"] == "device"

    def test_list_custom_field_definitions(self):
        """Test listing custom field definitions."""
        customer = Customer.objects.create(name="Test Corp")
        user = User.objects.create_user(username="admin", password="password", role="admin")
        user.customers.add(customer)

        # Create some custom field definitions
        CustomFieldDefinition.objects.create(
            customer=customer,
            name="asset_tag",
            label="Asset Tag",
            model_type="device",
            field_type="text",
        )
        CustomFieldDefinition.objects.create(
            customer=customer,
            name="warranty_expiry",
            label="Warranty Expiry",
            model_type="device",
            field_type="date",
        )

        client = APIClient()
        client.force_authenticate(user=user)

        response = client.get("/api/v1/custom-fields/")
        assert response.status_code == 200
        assert len(response.data["results"]) == 2

    def test_filter_by_model_type(self):
        """Test filtering custom fields by model type."""
        customer = Customer.objects.create(name="Test Corp")
        user = User.objects.create_user(username="admin", password="password", role="admin")
        user.customers.add(customer)

        # Create custom fields for different models
        CustomFieldDefinition.objects.create(
            customer=customer,
            name="asset_tag",
            label="Asset Tag",
            model_type="device",
            field_type="text",
        )
        CustomFieldDefinition.objects.create(
            customer=customer,
            name="ticket_number",
            label="Ticket Number",
            model_type="job",
            field_type="text",
        )

        client = APIClient()
        client.force_authenticate(user=user)

        response = client.get("/api/v1/custom-fields/?model_type=device")
        assert response.status_code == 200
        assert len(response.data["results"]) == 1
        assert response.data["results"][0]["model_type"] == "device"

    def test_validate_custom_field_value(self):
        """Test custom field value validation."""
        customer = Customer.objects.create(name="Test Corp")

        # Integer field with min/max validation
        field_def = CustomFieldDefinition.objects.create(
            customer=customer,
            name="port_count",
            label="Port Count",
            model_type="device",
            field_type="integer",
            validation_min=1,
            validation_max=48,
        )

        # Valid value
        is_valid, error = field_def.validate_value(24)
        assert is_valid
        assert error is None

        # Value too low
        is_valid, error = field_def.validate_value(0)
        assert not is_valid
        assert "must be >=" in error

        # Value too high
        is_valid, error = field_def.validate_value(100)
        assert not is_valid
        assert "must be <=" in error

    def test_required_field_validation(self):
        """Test required field validation."""
        customer = Customer.objects.create(name="Test Corp")

        field_def = CustomFieldDefinition.objects.create(
            customer=customer,
            name="location",
            label="Location",
            model_type="device",
            field_type="text",
            required=True,
        )

        # Missing required value
        is_valid, error = field_def.validate_value(None)
        assert not is_valid
        assert "is required" in error

        # Empty string for required field
        is_valid, error = field_def.validate_value("")
        assert not is_valid

        # Valid value
        is_valid, error = field_def.validate_value("Building A")
        assert is_valid
        assert error is None


@pytest.mark.django_db
class TestCustomFieldsOnModels:
    """Tests for custom fields on models."""

    def test_device_with_custom_fields(self):
        """Test device with custom field values."""
        customer = Customer.objects.create(name="Test Corp")
        user = User.objects.create_user(username="admin", password="password", role="admin")
        user.customers.add(customer)

        # Create custom field definition
        CustomFieldDefinition.objects.create(
            customer=customer,
            name="asset_tag",
            label="Asset Tag",
            model_type="device",
            field_type="text",
        )

        # Create credential
        cred = Credential.objects.create(customer=customer, name="cred1", username="user1")
        cred.password = "pass"
        cred.save()

        # Create device with custom field
        device = Device.objects.create(
            customer=customer,
            hostname="router1",
            mgmt_ip="192.168.1.1",
            vendor="cisco",
            platform="ios",
            credential=cred,
            custom_fields={"asset_tag": "A12345"},
        )

        assert device.custom_fields["asset_tag"] == "A12345"

        # Test API response includes custom fields
        client = APIClient()
        client.force_authenticate(user=user)

        response = client.get(f"/api/v1/devices/{device.id}/")
        assert response.status_code == 200
        assert "custom_fields" in response.data
        assert response.data["custom_fields"]["asset_tag"] == "A12345"

    def test_update_device_custom_fields(self):
        """Test updating device custom fields via API."""
        customer = Customer.objects.create(name="Test Corp")
        user = User.objects.create_user(username="admin", password="password", role="admin")
        user.customers.add(customer)

        # Create custom field definition
        CustomFieldDefinition.objects.create(
            customer=customer,
            name="location",
            label="Location",
            model_type="device",
            field_type="text",
        )

        # Create credential
        cred = Credential.objects.create(customer=customer, name="cred1", username="user1")
        cred.password = "pass"
        cred.save()

        # Create device
        device = Device.objects.create(
            customer=customer,
            hostname="router1",
            mgmt_ip="192.168.1.1",
            vendor="cisco",
            platform="ios",
            credential=cred,
            custom_fields={},
        )

        # Update device custom fields
        client = APIClient()
        client.force_authenticate(user=user)

        update_data = {
            "custom_fields": {"location": "Building A, Floor 2"},
        }

        response = client.patch(f"/api/v1/devices/{device.id}/", update_data, format="json")
        assert response.status_code == 200
        assert response.data["custom_fields"]["location"] == "Building A, Floor 2"

        # Verify in database
        device.refresh_from_db()
        assert device.custom_fields["location"] == "Building A, Floor 2"

    def test_custom_field_with_choices(self):
        """Test custom field with predefined choices."""
        customer = Customer.objects.create(name="Test Corp")

        field_def = CustomFieldDefinition.objects.create(
            customer=customer,
            name="environment",
            label="Environment",
            model_type="device",
            field_type="select",
            choices=["production", "staging", "development"],
        )

        # Valid choice
        is_valid, error = field_def.validate_value("production")
        assert is_valid
        assert error is None

        # Invalid choice
        is_valid, error = field_def.validate_value("testing")
        assert not is_valid
        assert "must be one of" in error

    def test_custom_field_multiselect(self):
        """Test multiselect custom field."""
        customer = Customer.objects.create(name="Test Corp")

        field_def = CustomFieldDefinition.objects.create(
            customer=customer,
            name="protocols",
            label="Protocols",
            model_type="device",
            field_type="multiselect",
            choices=["ssh", "telnet", "snmp", "netconf"],
        )

        # Valid multiselect
        is_valid, error = field_def.validate_value(["ssh", "snmp"])
        assert is_valid
        assert error is None

        # Invalid choice in list
        is_valid, error = field_def.validate_value(["ssh", "invalid_protocol"])
        assert not is_valid
        assert "Invalid choice" in error

    def test_custom_field_default_value(self):
        """Test custom field default value."""
        customer = Customer.objects.create(name="Test Corp")

        field_def = CustomFieldDefinition.objects.create(
            customer=customer,
            name="enabled",
            label="Enabled",
            model_type="device",
            field_type="boolean",
            default_value="true",
        )

        default = field_def.get_default()
        assert default is True

        # Test with integer
        field_def2 = CustomFieldDefinition.objects.create(
            customer=customer,
            name="priority",
            label="Priority",
            model_type="device",
            field_type="integer",
            default_value="5",
        )

        default2 = field_def2.get_default()
        assert default2 == 5
