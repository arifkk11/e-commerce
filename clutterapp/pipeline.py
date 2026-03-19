from django.contrib.auth import get_user_model
from django.utils import timezone
from django.contrib.auth import login as django_login


User = get_user_model()

def get_device_type(request):
    if not request:
        return 'Unknown'
    ua = request.META.get('HTTP_USER_AGENT', '').lower()
    if any(mobile in ua for mobile in ['iphone', 'android', 'blackberry', 'mobile']):
        return 'Mobile'
    elif any(tablet in ua for tablet in ['ipad', 'tablet', 'kindle']):
        return 'Tablet'
    else:
        return 'Desktop'

User = get_user_model()

def google_login_or_update_user(backend, user=None, response=None, *args, **kwargs):
    if backend.name != 'google-oauth2':
        return

    request = kwargs.get('request')
    email = response.get('email')
    google_uid = response.get('sub')
    picture = response.get('picture')

    # Find existing user by email
    existing_user = User.objects.filter(email=email).first()

    if existing_user:
        # Update existing user info
        existing_user.auth_provider = 'google'
        if picture:
            existing_user.picture_url = picture
        existing_user.login_time = timezone.now()
        existing_user.user_agent = request.META.get('HTTP_USER_AGENT') if request else ''
        existing_user.device_type = get_device_type(request)
        existing_user.save()

        # Explicitly log in user
        if request:
            django_login(request, existing_user, backend='django.contrib.auth.backends.ModelBackend')

        kwargs['user'] = existing_user
        return {'user': existing_user}

    # If no existing user, create new
    new_user = User.objects.create(
        email=email,
        name=email.split('@')[0],
        auth_provider='google',
        login_time=timezone.now(),
        user_agent=request.META.get('HTTP_USER_AGENT') if request else '',
        device_type=get_device_type(request),
        picture_url=picture
    )
  
    # Explicitly log in new user
    if request:
        django_login(request, new_user, backend='django.contrib.auth.backends.ModelBackend')

    kwargs['user'] = new_user
    return {'user': new_user}

def redirect_after_login(strategy, user, *args, **kwargs):
    if user.is_new_user:
        return strategy.redirect('/')   # onboarding page
    return strategy.redirect('/')               # normal homepage
