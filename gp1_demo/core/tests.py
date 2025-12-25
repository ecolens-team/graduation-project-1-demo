import pytest
from django.test import Client, RequestFactory
from django.core.files.uploadedfile import SimpleUploadedFile
from unittest.mock import patch
from .views import HomeView

# Check if Homepage Loads
@pytest.mark.django_db
def test_homepage_loads():
    client = Client()
    response = client.get('/')
    assert response.status_code == 200
    assert b"EcoLens Demo" in response.content
