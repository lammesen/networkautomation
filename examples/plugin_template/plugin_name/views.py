"""Views for the plugin."""

# Example DRF ViewSet:
# from rest_framework import viewsets
# from rest_framework.permissions import IsAuthenticated
# from webnet.api.permissions import RolePermission
# from webnet.api.mixins import CustomerScopedQuerysetMixin
# from .models import MyModel
# from .serializers import MyModelSerializer
#
# class MyModelViewSet(CustomerScopedQuerysetMixin, viewsets.ModelViewSet):
#     """API viewset for MyModel."""
#     
#     customer_field = "customer_id"
#     permission_classes = [IsAuthenticated, RolePermission]
#     queryset = MyModel.objects.all()
#     serializer_class = MyModelSerializer

# Example UI View:
# from django.shortcuts import render
# from django.contrib.auth.decorators import login_required
#
# @login_required
# def my_view(request):
#     """Custom UI view."""
#     context = {
#         "title": "My Page",
#     }
#     return render(request, "plugin_name/my_page.html", context)
