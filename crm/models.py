import uuid
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone


class Workspace(models.Model):
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    name = models.CharField(max_length=255)
    logo = models.ImageField(upload_to='workspace/logos/', blank=True, null=True)
    favicon = models.ImageField(upload_to='workspace/favicons/', blank=True, null=True)
    primary_color = models.CharField(max_length=7, default='#3B82F6')
    secondary_color = models.CharField(max_length=7, default='#10B981')
    accent_color = models.CharField(max_length=7, default='#F59E0B')
    company_name = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.name


class User(AbstractUser):
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    workspace = models.ForeignKey(Workspace, on_delete=models.CASCADE, null=True, blank=True)
    role = models.CharField(max_length=20, choices=[
        ('OWNER', 'Owner'),
        ('ADMIN', 'Admin'),
        ('MANAGER', 'Manager'),
        ('STAFF', 'Staff'),
        ('VIEWER', 'Viewer'),
    ], default='VIEWER')
    avatar = models.ImageField(upload_to='users/avatars/', blank=True, null=True)
    phone = models.CharField(max_length=20, blank=True)
    language = models.CharField(max_length=10, default='en', blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_deleted = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.get_full_name() or self.username

    def soft_delete(self):
        self.is_deleted = True
        self.deleted_at = timezone.now()
        self.save()


class AuditLog(models.Model):
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    workspace = models.ForeignKey(Workspace, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    action = models.CharField(max_length=50)
    model_name = models.CharField(max_length=100)
    object_id = models.UUIDField(null=True)
    changes = models.JSONField(null=True, blank=True)
    ip_address = models.GenericIPAddressField(null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user} - {self.action} - {self.model_name}"


class Tag(models.Model):
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    workspace = models.ForeignKey(Workspace, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    color = models.CharField(max_length=7, default='#3B82F6')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']
        unique_together = ['workspace', 'name']

    def __str__(self):
        return self.name


class Company(models.Model):
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    workspace = models.ForeignKey(Workspace, on_delete=models.CASCADE)
    name = models.CharField(max_length=255)
    legal_name = models.CharField(max_length=255, blank=True)
    website = models.URLField(blank=True)
    industry = models.CharField(max_length=100, blank=True)
    phone = models.CharField(max_length=20, blank=True)
    email = models.EmailField(blank=True)
    address = models.TextField(blank=True)
    description = models.TextField(blank=True)
    logo = models.ImageField(upload_to='companies/logos/', blank=True, null=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='companies_created')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_deleted = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(null=True, blank=True)
    is_workspace = models.BooleanField(
        default=False,
        db_index=True,
        help_text="True for the company that mirrors this workspace. Cannot be deleted.",
    )

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.name

    def soft_delete(self):
        self.is_deleted = True
        self.deleted_at = timezone.now()
        self.save()


class CompanyAccess(models.Model):
    ROLE_CHOICES = [
        ('MANAGER', 'Manager'),
        ('EDITOR', 'Editor'),
        ('VIEWER', 'Viewer'),
    ]
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    company = models.ForeignKey(Company, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='VIEWER')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['company', 'user']

    def __str__(self):
        return f"{self.user} - {self.company} ({self.role})"


class Contact(models.Model):
    GENDER_CHOICES = [
        ('MALE', 'Male'),
        ('FEMALE', 'Female'),
        ('OTHER', 'Other'),
        ('PREFER_NOT_TO_SAY', 'Prefer not to say'),
    ]
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    workspace = models.ForeignKey(Workspace, on_delete=models.CASCADE)
    first_name = models.CharField(max_length=100)
    middle_name = models.CharField(max_length=100, blank=True)
    last_name = models.CharField(max_length=100, blank=True)
    nickname = models.CharField(max_length=100, blank=True)
    birthday = models.DateField(null=True, blank=True)
    gender = models.CharField(max_length=20, choices=GENDER_CHOICES, blank=True)
    personal_email = models.EmailField(blank=True)
    work_email = models.EmailField(blank=True)
    personal_phone = models.CharField(max_length=20, blank=True)
    work_phone = models.CharField(max_length=20, blank=True)
    company = models.ForeignKey(Company, on_delete=models.SET_NULL, null=True, blank=True, related_name='contacts')
    notes = models.TextField(blank=True)
    address = models.TextField(blank=True)
    country = models.ForeignKey('Country', on_delete=models.SET_NULL, null=True, blank=True, related_name='contacts')
    state = models.ForeignKey('State', on_delete=models.SET_NULL, null=True, blank=True, related_name='contacts')
    city = models.ForeignKey('City', on_delete=models.SET_NULL, null=True, blank=True, related_name='contacts')
    website = models.URLField(blank=True)
    avatar = models.ImageField(upload_to='contacts/avatars/', blank=True, null=True)
    tags = models.ManyToManyField(Tag, blank=True, related_name='contacts')
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='contacts_created')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_deleted = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(null=True, blank=True)
    
    linkedin = models.URLField(blank=True)
    github = models.URLField(blank=True)
    facebook = models.URLField(blank=True)
    instagram = models.URLField(blank=True)
    twitter = models.URLField(blank=True)
    tiktok = models.URLField(blank=True)
    youtube = models.URLField(blank=True)
    telegram = models.URLField(blank=True)
    discord = models.CharField(max_length=100, blank=True)
    custom_social_profiles = models.JSONField(default=list, blank=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name_plural = 'Contacts'

    def __str__(self):
        return self.full_name or self.first_name

    @property
    def full_name(self):
        return " ".join(
            part for part in (self.first_name, self.middle_name, self.last_name) if part
        ).strip()

    def soft_delete(self):
        self.is_deleted = True
        self.deleted_at = timezone.now()
        self.save()

    def get_socials(self):
        return {
            'linkedin': self.linkedin,
            'github': self.github,
            'facebook': self.facebook,
            'instagram': self.instagram,
            'twitter': self.twitter,
            'tiktok': self.tiktok,
            'youtube': self.youtube,
            'telegram': self.telegram,
            'discord': self.discord,
            'custom': self.custom_social_profiles,
            'has_any': bool(self.linkedin or self.github or self.facebook or self.instagram or self.twitter or self.tiktok or self.youtube or self.telegram or self.discord or self.custom_social_profiles)
        }


class ContactCompanyRelationship(models.Model):
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    contact = models.ForeignKey(Contact, on_delete=models.CASCADE, related_name='company_relationships')
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='contact_relationships')
    position = models.CharField(max_length=100, blank=True)
    department = models.CharField(max_length=100, blank=True)
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    is_current = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-is_current', '-start_date']

    def __str__(self):
        return f"{self.contact} at {self.company}"


class Note(models.Model):
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    workspace = models.ForeignKey(Workspace, on_delete=models.CASCADE)
    contact = models.ForeignKey(Contact, on_delete=models.CASCADE, null=True, blank=True, related_name='contact_notes')
    company = models.ForeignKey(Company, on_delete=models.CASCADE, null=True, blank=True, related_name='notes')
    author = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    title = models.CharField(max_length=255, blank=True)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_deleted = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.title or f"Note by {self.author}"


class Activity(models.Model):
    ACTIVITY_TYPES = [
        ('CALL', 'Call'),
        ('EMAIL', 'Email'),
        ('MEETING', 'Meeting'),
        ('WHATSAPP', 'WhatsApp'),
        ('NOTE', 'Note'),
        ('OTHER', 'Other'),
    ]
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    workspace = models.ForeignKey(Workspace, on_delete=models.CASCADE)
    contact = models.ForeignKey(Contact, on_delete=models.CASCADE, null=True, blank=True, related_name='activities')
    company = models.ForeignKey(Company, on_delete=models.CASCADE, null=True, blank=True, related_name='activities')
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    activity_type = models.CharField(max_length=20, choices=ACTIVITY_TYPES)
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    due_date = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    is_completed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_deleted = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.activity_type} - {self.title}"


class CustomField(models.Model):
    FIELD_TYPES = [
        ('TEXT', 'Text'),
        ('NUMBER', 'Number'),
        ('DATE', 'Date'),
        ('BOOLEAN', 'Boolean'),
        ('SELECT', 'Select'),
        ('MULTISELECT', 'Multi-select'),
    ]
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    workspace = models.ForeignKey(Workspace, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    field_type = models.CharField(max_length=20, choices=FIELD_TYPES)
    model = models.CharField(max_length=50)
    options = models.JSONField(null=True, blank=True)
    required = models.BooleanField(default=False)
    order = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['order', 'name']

    def __str__(self):
        return f"{self.name} ({self.field_type})"


class CustomFieldValue(models.Model):
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    custom_field = models.ForeignKey(CustomField, on_delete=models.CASCADE)
    content_type = models.ForeignKey('contenttypes.ContentType', on_delete=models.CASCADE)
    object_id = models.UUIDField()
    value = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['custom_field', 'content_type', 'object_id']

    def __str__(self):
        return f"{self.custom_field.name} - {self.object_id}"


class Country(models.Model):
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    name_es = models.CharField(max_length=100)
    name_en = models.CharField(max_length=100)
    code = models.CharField(max_length=3)  # ISO code like CHL, MEX, USA
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name_es']
        verbose_name_plural = 'countries'

    def __str__(self):
        return self.name_es

    def get_name(self, lang='es'):
        return self.name_en if lang == 'en' else self.name_es


class State(models.Model):
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    country = models.ForeignKey(Country, on_delete=models.CASCADE, related_name='states')
    name_es = models.CharField(max_length=100)
    name_en = models.CharField(max_length=100)
    code = models.CharField(max_length=10, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name_es']

    def __str__(self):
        return self.name_es

    def get_name(self, lang='es'):
        return self.name_en if lang == 'en' else self.name_es


class City(models.Model):
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    state = models.ForeignKey(State, on_delete=models.CASCADE, related_name='cities')
    name_es = models.CharField(max_length=100)
    name_en = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name_es']

    def __str__(self):
        return self.name_es

    def get_name(self, lang='es'):
        return self.name_en if lang == 'en' else self.name_es