import os
import sys
import django

# Add the current directory to sys.path
sys.path.append(os.getcwd())

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'service_booking.settings')
django.setup()

from django.conf import settings
from django.template import loader
from django.test import RequestFactory
from django.contrib.auth.models import AnonymousUser
from bookings.models import CustomUser
from bookings.forms import LoginForm
from django.contrib.auth.forms import SetPasswordForm

def test_render():
    rf = RequestFactory()
    request = rf.get('/login/')
    request.user = AnonymousUser()
    
    print("Testing login.html rendering...")
    try:
        form = LoginForm(request)
        t = loader.get_template('bookings/login.html')
        c = {'form': form, 'request': request}
        t.render(c)
        print("login.html rendered successfully.")
    except Exception as e:
        print(f"Error rendering login.html: {e}")
        import traceback
        traceback.print_exc()

    print("\nTesting force_password_change.html rendering...")
    try:
        user = CustomUser.objects.filter(username='anand-s-bosco').first()
        if not user:
            print("User anand-s-bosco not found.")
            # Try any user
            user = CustomUser.objects.first()
            if not user:
                print("No users found in database.")
                return
        
        request.user = user
        form = SetPasswordForm(user)
        t = loader.get_template('bookings/force_password_change.html')
        c = {'form': form, 'request': request}
        t.render(c)
        print("force_password_change.html rendered successfully.")
    except Exception as e:
        print(f"Error rendering force_password_change.html: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_render()
