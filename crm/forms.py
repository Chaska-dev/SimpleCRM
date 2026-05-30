from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import User, Workspace


class UserRegistrationForm(UserCreationForm):
    email = forms.EmailField(required=True)
    first_name = forms.CharField(max_length=100, required=True)
    last_name = forms.CharField(max_length=100, required=True)
    workspace_name = forms.CharField(max_length=255, required=True, label='Company/Workspace Name')

    class Meta:
        model = User
        fields = ['username', 'email', 'first_name', 'last_name', 'password1', 'password2']

    def save(self, commit=True):
        workspace = Workspace.objects.create(name=self.cleaned_data['workspace_name'])
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        user.first_name = self.cleaned_data['first_name']
        user.last_name = self.cleaned_data['last_name']
        user.workspace = workspace
        user.role = 'OWNER'
        if commit:
            user.save()
        return user


class LoginForm(forms.Form):
    username = forms.CharField(widget=forms.TextInput(attrs={
        'class': 'w-full px-4 py-3 rounded-lg bg-gray-800 border border-gray-700 text-gray-100 placeholder-gray-500 focus:outline-none focus:border-blue-500 transition-colors',
        'placeholder': 'Enter your username'
    }))
    password = forms.CharField(widget=forms.PasswordInput(attrs={
        'class': 'w-full px-4 py-3 rounded-lg bg-gray-800 border border-gray-700 text-gray-100 placeholder-gray-500 focus:outline-none focus:border-blue-500 transition-colors',
        'placeholder': '••••••••'
    }))


class WorkspaceSettingsForm(forms.ModelForm):
    class Meta:
        model = Workspace
        fields = ['name', 'logo', 'favicon', 'primary_color', 'secondary_color', 'accent_color', 'company_name']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'w-full px-4 py-2 rounded-lg bg-gray-800 border border-gray-700 text-gray-100'}),
            'primary_color': forms.TextInput(attrs={'type': 'color', 'class': 'w-12 h-10 rounded cursor-pointer'}),
            'secondary_color': forms.TextInput(attrs={'type': 'color', 'class': 'w-12 h-10 rounded cursor-pointer'}),
            'accent_color': forms.TextInput(attrs={'type': 'color', 'class': 'w-12 h-10 rounded cursor-pointer'}),
            'company_name': forms.TextInput(attrs={'class': 'w-full px-4 py-2 rounded-lg bg-gray-800 border border-gray-700 text-gray-100'}),
        }