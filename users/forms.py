"""
Forms module for users app.
"""
from django.forms import ModelForm
from django.contrib.auth import forms as auth_forms
from django.contrib.auth import models as auth_models
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Fieldset, ButtonHolder, Submit

class SaveLayout(Layout):
    """Layout class with a 'Save'-Button at the end."""
    def __init__(self, *fields):
        super().__init__(*fields)
        self.fields.append(
            ButtonHolder(
                Submit('Save', 'Save')
            )
        )

class CustomAuthentificationForm(auth_forms.AuthenticationForm):
    """Log in form."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.layout = Layout(
            Fieldset(
                'Log In',
                'username',
                'password'
            ),
            ButtonHolder(
                Submit('Log In', 'Log In')
            )
        )

class ProfileForm(ModelForm):
    """User profile form."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.layout = SaveLayout(
            Fieldset(
                'Edit Profile',
                'first_name',
                'last_name'
            )
        )
    class Meta:
        model = auth_models.User
        fields = ['first_name', 'last_name']

class RegistrationForm(auth_forms.UserCreationForm):
    """User registration form."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.layout = SaveLayout(
            Fieldset(
                'User Registration',
                'username',
                'password1',
                'password2'
            )
        )
