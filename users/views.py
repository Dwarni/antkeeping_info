"""
Module for views of users app.
"""
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import UpdateView
from .forms import ProfileForm


# Create your views here.
class UserProfileView(LoginRequiredMixin, UpdateView):
    """User profile view."""
    template_name = 'users/profile.html'
    form_class = ProfileForm
    success_url = '/'

    def get_object(self, queryset=None):
        return self.request.user
