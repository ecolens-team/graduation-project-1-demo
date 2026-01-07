import pytest
from django.test import Client


@pytest.mark.django_db
def test_login_page_loads():
    client = Client()
    # Go directly to /login/
    response = client.get('/login/')
    
    assert response.status_code == 200
    assert b"Username" in response.content