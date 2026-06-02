from django.contrib.auth.decorators import user_passes_test
from django.shortcuts import redirect
from django.contrib import messages
from functools import wraps

def admin_required(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login')
        if not request.user.is_staff and not request.user.is_superuser:
            messages.error(request, 'Admin access required.')
            return redirect('customer_home')
        return view_func(request, *args, **kwargs)
    return _wrapped_view
