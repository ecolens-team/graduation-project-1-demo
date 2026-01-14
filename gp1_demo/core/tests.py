import pytest
from django.test import Client


@pytest.mark.django_db
def test_login_page_loads():
    client = Client()
    response = client.get('/login/')
    
    assert response.status_code == 200
    assert b"Username" in response.content
@pytest.mark.django_db

def test_home_page_loads():
    client = Client()
    response = client.get('/')
    
    assert response.status_code == 302
    assert response.url.startswith('/login/')

@pytest.mark.django_db
def test_observation_creation():
    from django.contrib.auth.models import User
    from core.models import Observation
    from django.core.files.uploadedfile import SimpleUploadedFile
    
    client = Client()
    user = User.objects.create_user(username='testuser', password='testpass123')
    client.login(username='testuser', password='testpass123')
    
    image = SimpleUploadedFile(
        name='test_image.jpg',
        content=b'\x89PNG\r\n\x1a\n\x00\x00', 
        content_type='image/jpeg'
    )
    
    client.post('/upload/', {'image': image}, follow=True)
    
    assert Observation.objects.count() == 1
    obs = Observation.objects.first()
    assert obs.user == user
    assert obs.image is not None