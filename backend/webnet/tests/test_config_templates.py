"""Tests for Configuration Template Library (Issue #16)."""

import pytest
from django.urls import reverse
from rest_framework import status

from webnet.config_mgmt.models import ConfigTemplate


@pytest.fixture
def config_template(db, customer, admin_user):
    """Create a test configuration template."""
    return ConfigTemplate.objects.create(
        customer=customer,
        name="Base Config",
        description="Basic device configuration template",
        category="base",
        template_content="""hostname {{ hostname }}
!
interface {{ interface }}
 ip address {{ ip_address }} {{ subnet_mask }}
 no shutdown
!
""",
        variables_schema={
            "hostname": {"type": "string", "required": True, "description": "Device hostname"},
            "interface": {
                "type": "string",
                "required": True,
                "default": "GigabitEthernet0/0",
            },
            "ip_address": {"type": "ipaddress", "required": True},
            "subnet_mask": {
                "type": "string",
                "required": False,
                "default": "255.255.255.0",
            },
        },
        platform_tags=["cisco_ios", "cisco_iosxe"],
        is_active=True,
        created_by=admin_user,
    )


class TestConfigTemplateModel:
    """Tests for ConfigTemplate model."""

    def test_get_variables(self, config_template):
        """Test getting variables schema as dictionary."""
        variables = config_template.get_variables()
        assert "hostname" in variables
        assert variables["hostname"]["type"] == "string"
        assert variables["hostname"]["required"] is True

    def test_validate_variables_valid(self, config_template):
        """Test variable validation with valid values."""
        variables = {
            "hostname": "router1",
            "interface": "GigabitEthernet0/1",
            "ip_address": "192.168.1.1",
        }
        is_valid, errors = config_template.validate_variables(variables)
        assert is_valid is True
        assert len(errors) == 0

    def test_validate_variables_missing_required(self, config_template):
        """Test variable validation with missing required field."""
        variables = {
            "interface": "GigabitEthernet0/1",
            "ip_address": "192.168.1.1",
        }
        is_valid, errors = config_template.validate_variables(variables)
        assert is_valid is False
        assert any("hostname" in e for e in errors)

    def test_validate_variables_invalid_ip(self, config_template):
        """Test variable validation with invalid IP address."""
        variables = {
            "hostname": "router1",
            "interface": "GigabitEthernet0/1",
            "ip_address": "invalid-ip",
        }
        is_valid, errors = config_template.validate_variables(variables)
        assert is_valid is False
        assert any("ip_address" in e for e in errors)

    def test_render_template(self, config_template):
        """Test rendering template with valid variables."""
        variables = {
            "hostname": "router1",
            "interface": "GigabitEthernet0/1",
            "ip_address": "192.168.1.1",
        }
        rendered = config_template.render(variables)
        assert "hostname router1" in rendered
        assert "interface GigabitEthernet0/1" in rendered
        assert "ip address 192.168.1.1 255.255.255.0" in rendered

    def test_render_template_with_defaults(self, config_template):
        """Test rendering uses default values."""
        variables = {
            "hostname": "router1",
            "ip_address": "192.168.1.1",
        }
        rendered = config_template.render(variables)
        assert "interface GigabitEthernet0/0" in rendered  # Default value

    def test_render_template_validation_error(self, config_template):
        """Test rendering fails with invalid variables."""
        variables = {"interface": "GigabitEthernet0/1"}  # Missing required hostname
        with pytest.raises(ValueError) as excinfo:
            config_template.render(variables)
        assert "hostname" in str(excinfo.value).lower()


@pytest.mark.django_db
class TestConfigTemplateAPI:
    """Tests for ConfigTemplate API endpoints."""

    def test_list_templates(self, api_client, admin_user, config_template):
        """Test listing configuration templates."""
        api_client.force_authenticate(user=admin_user)
        response = api_client.get(reverse("config-template-list"))
        assert response.status_code == status.HTTP_200_OK
        # Handle paginated and non-paginated responses
        results = response.data.get("results", response.data)
        if isinstance(results, dict):
            results = [results]
        assert len(results) >= 1
        assert any(t["name"] == "Base Config" for t in results)

    def test_list_templates_filter_by_category(
        self, api_client, admin_user, config_template, customer
    ):
        """Test filtering templates by category."""
        # Create another template with different category
        ConfigTemplate.objects.create(
            customer=customer,
            name="Interface Template",
            category="interface",
            template_content="interface {{ name }}",
            created_by=admin_user,
        )

        api_client.force_authenticate(user=admin_user)
        response = api_client.get(reverse("config-template-list"), {"category": "base"})
        assert response.status_code == status.HTTP_200_OK
        # Handle paginated and non-paginated responses
        results = response.data.get("results", response.data)
        if isinstance(results, dict):
            results = [results]
        assert all(t["category"] == "base" for t in results)

    def test_create_template(self, api_client, admin_user, customer):
        """Test creating a new template."""
        api_client.force_authenticate(user=admin_user)
        data = {
            "customer": customer.id,
            "name": "New Template",
            "description": "Test template",
            "category": "custom",
            "template_content": "hostname {{ hostname }}",
            "variables_schema": {"hostname": {"type": "string", "required": True}},
            "is_active": True,
        }
        response = api_client.post(reverse("config-template-list"), data, format="json")
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["name"] == "New Template"
        assert response.data["created_by"] == admin_user.id

    def test_update_template(self, api_client, admin_user, config_template):
        """Test updating a template."""
        api_client.force_authenticate(user=admin_user)
        data = {"name": "Updated Name", "description": "Updated description"}
        response = api_client.patch(
            reverse("config-template-detail", args=[config_template.id]), data, format="json"
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.data["name"] == "Updated Name"

    def test_delete_template(self, api_client, admin_user, config_template):
        """Test deleting a template."""
        api_client.force_authenticate(user=admin_user)
        response = api_client.delete(reverse("config-template-detail", args=[config_template.id]))
        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert not ConfigTemplate.objects.filter(id=config_template.id).exists()

    def test_render_endpoint(self, api_client, admin_user, config_template):
        """Test the render action endpoint."""
        api_client.force_authenticate(user=admin_user)
        data = {
            "variables": {
                "hostname": "test-router",
                "interface": "GigabitEthernet0/1",
                "ip_address": "10.0.0.1",
            }
        }
        response = api_client.post(
            reverse("config-template-render", args=[config_template.id]), data, format="json"
        )
        assert response.status_code == status.HTTP_200_OK
        assert "rendered_config" in response.data
        assert "hostname test-router" in response.data["rendered_config"]

    def test_render_with_device_context(self, api_client, admin_user, config_template, device):
        """Test rendering with device context."""
        api_client.force_authenticate(user=admin_user)
        data = {
            "variables": {"interface": "GigabitEthernet0/1", "ip_address": "10.0.0.1"},
            "device_id": device.id,
        }
        response = api_client.post(
            reverse("config-template-render", args=[config_template.id]), data, format="json"
        )
        assert response.status_code == status.HTTP_200_OK
        assert device.hostname in response.data["rendered_config"]

    def test_validate_endpoint(self, api_client, admin_user, config_template):
        """Test the validate action endpoint."""
        api_client.force_authenticate(user=admin_user)
        response = api_client.get(reverse("config-template-validate", args=[config_template.id]))
        assert response.status_code == status.HTTP_200_OK
        assert response.data["valid"] is True

    def test_validate_invalid_template(self, api_client, admin_user, customer):
        """Test validating an invalid template."""
        invalid_template = ConfigTemplate.objects.create(
            customer=customer,
            name="Invalid Template",
            category="custom",
            template_content="{% if x %}missing endif",
            created_by=admin_user,
        )
        api_client.force_authenticate(user=admin_user)
        response = api_client.get(reverse("config-template-validate", args=[invalid_template.id]))
        assert response.status_code == status.HTTP_200_OK
        assert response.data["valid"] is False
        assert len(response.data["errors"]) > 0

    def test_categories_endpoint(self, api_client, admin_user, config_template):
        """Test the categories action endpoint."""
        api_client.force_authenticate(user=admin_user)
        response = api_client.get(reverse("config-template-categories"))
        assert response.status_code == status.HTTP_200_OK
        assert "categories" in response.data
        assert "choices" in response.data

    def test_tenant_isolation(self, api_client, operator_user, config_template, other_customer):
        """Test that operators can't see other customer's templates."""
        # Create template for other customer
        other_template = ConfigTemplate.objects.create(
            customer=other_customer,
            name="Other Template",
            category="custom",
            template_content="test",
        )

        api_client.force_authenticate(user=operator_user)
        response = api_client.get(reverse("config-template-list"))
        assert response.status_code == status.HTTP_200_OK

        # Handle paginated and non-paginated responses
        results = response.data.get("results", response.data)
        if isinstance(results, dict):
            results = [results]

        # Should not see the other customer's template
        template_ids = [t["id"] for t in results]
        assert other_template.id not in template_ids
