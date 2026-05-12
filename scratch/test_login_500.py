import os
import sys
import django
from django.test import RequestFactory
from django.contrib.auth import authenticate

# Setup Django
sys.path.append(os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "service_booking.settings")
django.setup()

from bookings.views import login_view
from django.urls import reverse

def test_login_post():
    factory = RequestFactory()
    # Mock a POST request to login
    # Even with wrong credentials, it shouldn't 500
    data = {
        'username': 'test@example.com',
        'password': 'wrongpassword'
    }
    request = factory.post(reverse('login'), data=data)
    
    # We need to add session and messages middleware if we want to run the view directly
    from django.contrib.sessions.middleware import SessionMiddleware
    from django.contrib.messages.storage.fallback import FallbackStorage

    middleware = SessionMiddleware(lambda r: None)
    middleware.process_request(request)
    request.session.save()
    
    setattr(request, '_messages', FallbackStorage(request))

    print("Sending POST request to login_view...")
    try:
        response = login_view(request)
        print(f"Response status code: {response.status_code}")
        if response.status_code == 500:
            print("Detected 500 error!")
        else:
            print("No 500 error detected for invalid credentials.")
    except Exception as e:
        print(f"Exception caught during login_view: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_login_post()
