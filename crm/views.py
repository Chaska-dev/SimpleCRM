from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth.forms import PasswordChangeForm
from django.core.files.uploadedfile import InMemoryUploadedFile
from .forms import UserRegistrationForm, LoginForm
from .models import Contact, Company
import io
from PIL import Image


def register(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    
    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, 'Account created successfully!')
            return redirect('dashboard')
    else:
        form = UserRegistrationForm()
    
    return render(request, 'auth/register.html', {'form': form})


def login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    
    if request.method == 'POST':
        form = LoginForm(request.POST)
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect('dashboard')
        else:
            messages.error(request, 'Invalid username or password')
    else:
        form = LoginForm()
    
    return render(request, 'auth/login.html', {'form': form})


def logout_view(request):
    logout(request)
    return redirect('login')


@login_required
def dashboard(request):
    contacts = Contact.objects.filter(workspace=request.user.workspace, is_deleted=False).select_related().prefetch_related('company_relationships__company')
    companies = Company.objects.filter(workspace=request.user.workspace, is_deleted=False)
    
    context = {
        'contacts': contacts,
        'contacts_count': contacts.count(),
        'companies_count': companies.count(),
    }
    return render(request, 'dashboard.html', context)


@login_required
def contacts(request):
    contacts = Contact.objects.filter(workspace=request.user.workspace, is_deleted=False)
    context = {'contacts': contacts}
    return render(request, 'contacts/list.html', context)


@login_required
def contact_create(request):
    if request.method == 'POST':
        first_name = request.POST.get('first_name')
        middle_name = request.POST.get('middle_name', '')
        last_name = request.POST.get('last_name', '')
        nickname = request.POST.get('nickname', '')
        gender = request.POST.get('gender', '')
        birthday = request.POST.get('birthday', '') or None
        personal_email = request.POST.get('personal_email', '')
        work_email = request.POST.get('work_email', '')
        personal_phone = request.POST.get('personal_phone', '')
        work_phone = request.POST.get('work_phone', '')
        job_title = request.POST.get('job_title', '')
        website = request.POST.get('website', '')
        address = request.POST.get('address', '')
        city = request.POST.get('city', '')
        state = request.POST.get('state', '')
        country = request.POST.get('country', '')
        notes = request.POST.get('notes', '')
        
        linkedin = request.POST.get('linkedin', '')
        github = request.POST.get('github', '')
        facebook = request.POST.get('facebook', '')
        instagram = request.POST.get('instagram', '')
        twitter = request.POST.get('twitter', '')
        tiktok = request.POST.get('tiktok', '')
        youtube = request.POST.get('youtube', '')
        telegram = request.POST.get('telegram', '')
        discord = request.POST.get('discord', '')
        
        custom_social_profiles = request.POST.get('custom_social_profiles', '[]')
        if custom_social_profiles:
            import json
            custom_social_profiles = json.loads(custom_social_profiles)
        
        avatar_file = request.FILES.get('avatar')
        cropped_avatar = None
        
        crop_x = request.POST.get('crop_x', '0')
        crop_y = request.POST.get('crop_y', '0')
        crop_size = request.POST.get('crop_size', '50')
        
        print(f"Avatar file: {avatar_file}")
        print(f"Crop values: crop_x={crop_x}, crop_y={crop_y}, crop_size={crop_size}")
        print(f"POST keys: {list(request.POST.keys())}")
        print(f"FILES keys: {list(request.FILES.keys())}")
        
        if avatar_file and avatar_file.content_type.startswith('image/'):
            from PIL import Image
            import io
            
            img = Image.open(avatar_file)
            print(f"Original image size: {img.width}x{img.height}")
            
            if img.mode in ('RGBA', 'P'):
                img = img.convert('RGB')
            target_size = (400, 400)
            img_ratio = img.width / img.height
            
            if img_ratio > 1:
                new_height = target_size[1]
                new_width = int(new_height * img_ratio)
            else:
                new_width = target_size[0]
                new_height = int(new_width / img_ratio)
            
            img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
            
            try:
                offset_x_percent = float(crop_x)
                offset_y_percent = float(crop_y)
                size_percent = float(crop_size)
                
                offset_x_px = int((offset_x_percent / 100) * new_width)
                offset_y_px = int((offset_y_percent / 100) * new_height)
                
                crop_px = int((size_percent / 100) * new_width)
                crop_px = max(50, min(crop_px, min(new_width, new_height)))
            except (ValueError, ZeroDivisionError):
                offset_x_px = 0
                offset_y_px = 0
                crop_px = target_size[0]
            
            left = max(0, offset_x_px)
            top = max(0, offset_y_px)
            right = min(new_width, left + crop_px)
            bottom = min(new_height, top + crop_px)
            
            if right - left < crop_px:
                left = max(0, right - crop_px)
            if bottom - top < crop_px:
                top = max(0, bottom - crop_px)
            
            img = img.crop((left, top, right, bottom))
            
            if img.width != target_size[0] or img.height != target_size[1]:
                img = img.resize(target_size, Image.Resampling.LANCZOS)
            
            output = io.BytesIO()
            img.save(output, format='PNG', quality=90)
            output.seek(0)
            
            from django.core.files.uploadedfile import InMemoryUploadedFile
            cropped_avatar = InMemoryUploadedFile(
                output,
                'avatar',
                f'contact_avatar.png',
                'image/png',
                output.getbuffer().nbytes,
                None
            )
        
        contact = Contact.objects.create(
            workspace=request.user.workspace,
            first_name=first_name,
            middle_name=middle_name,
            last_name=last_name,
            nickname=nickname,
            gender=gender,
            birthday=birthday,
            personal_email=personal_email,
            work_email=work_email,
            personal_phone=personal_phone,
            work_phone=work_phone,
            job_title=job_title,
            website=website,
            address=address,
            city=city,
            state=state,
            country=country,
            notes=notes,
            linkedin=linkedin,
            github=github,
            facebook=facebook,
            instagram=instagram,
            twitter=twitter,
            tiktok=tiktok,
            youtube=youtube,
            telegram=telegram,
            discord=discord,
            custom_social_profiles=custom_social_profiles,
            avatar=cropped_avatar,
            created_by=request.user
        )
        messages.success(request, 'Contact created successfully!')
        return redirect('contacts')
    
    return render(request, 'contacts/create.html')


@login_required
def contact_edit(request, contact_uuid):
    contact = get_object_or_404(Contact, uuid=contact_uuid, workspace=request.user.workspace, is_deleted=False)
    
    if request.method == 'POST':
        contact.first_name = request.POST.get('first_name', contact.first_name)
        contact.middle_name = request.POST.get('middle_name', '')
        contact.last_name = request.POST.get('last_name', '')
        contact.nickname = request.POST.get('nickname', '')
        contact.gender = request.POST.get('gender', '')
        contact.birthday = request.POST.get('birthday', '') or None
        contact.personal_email = request.POST.get('personal_email', '')
        contact.work_email = request.POST.get('work_email', '')
        contact.personal_phone = request.POST.get('personal_phone', '')
        contact.work_phone = request.POST.get('work_phone', '')
        contact.job_title = request.POST.get('job_title', '')
        contact.website = request.POST.get('website', '')
        contact.address = request.POST.get('address', '')
        contact.city = request.POST.get('city', '')
        contact.state = request.POST.get('state', '')
        contact.country = request.POST.get('country', '')
        contact.notes = request.POST.get('notes', '')
        
        contact.linkedin = request.POST.get('linkedin', '')
        contact.github = request.POST.get('github', '')
        contact.facebook = request.POST.get('facebook', '')
        contact.instagram = request.POST.get('instagram', '')
        contact.twitter = request.POST.get('twitter', '')
        contact.tiktok = request.POST.get('tiktok', '')
        contact.youtube = request.POST.get('youtube', '')
        contact.telegram = request.POST.get('telegram', '')
        contact.discord = request.POST.get('discord', '')
        
        custom_social_profiles = request.POST.get('custom_social_profiles', '[]')
        if custom_social_profiles:
            import json
            contact.custom_social_profiles = json.loads(custom_social_profiles)
        
        avatar_file = request.FILES.get('avatar')
        if avatar_file and avatar_file.content_type.startswith('image/'):
            from PIL import Image
            import io
            
            img = Image.open(avatar_file)
            
            if img.mode in ('RGBA', 'P'):
                img = img.convert('RGB')
            target_size = (400, 400)
            img_ratio = img.width / img.height
            
            if img_ratio > 1:
                new_height = target_size[1]
                new_width = int(new_height * img_ratio)
            else:
                new_width = target_size[0]
                new_height = int(new_width / img_ratio)
            
            img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
            
            crop_x = request.POST.get('crop_x', '0')
            crop_y = request.POST.get('crop_y', '0')
            crop_size = request.POST.get('crop_size', '50')
            
            try:
                offset_x_percent = float(crop_x)
                offset_y_percent = float(crop_y)
                size_percent = float(crop_size)
                
                offset_x_px = int((offset_x_percent / 100) * new_width)
                offset_y_px = int((offset_y_percent / 100) * new_height)
                
                crop_px = int((size_percent / 100) * new_width)
                crop_px = max(50, min(crop_px, min(new_width, new_height)))
            except (ValueError, ZeroDivisionError):
                offset_x_px = 0
                offset_y_px = 0
                crop_px = target_size[0]
            
            left = max(0, offset_x_px)
            top = max(0, offset_y_px)
            right = min(new_width, left + crop_px)
            bottom = min(new_height, top + crop_px)
            
            if right - left < crop_px:
                left = max(0, right - crop_px)
            if bottom - top < crop_px:
                top = max(0, bottom - crop_px)
            
            img = img.crop((left, top, right, bottom))
            
            if img.width != target_size[0] or img.height != target_size[1]:
                img = img.resize(target_size, Image.Resampling.LANCZOS)
            
            output = io.BytesIO()
            img.save(output, format='PNG', quality=90)
            output.seek(0)
            
            if contact.avatar:
                contact.avatar.delete(save=False)
            contact.avatar = InMemoryUploadedFile(
                output,
                'avatar',
                f'contact_avatar.png',
                'image/png',
                output.getbuffer().nbytes,
                None
            )
        
        contact.save()
        messages.success(request, 'Contact updated successfully!')
        return redirect('contacts')
    
    context = {'contact': contact, 'custom_social_profiles_json': contact.custom_social_profiles}
    return render(request, 'contacts/edit.html', context)


@login_required
def settings(request):
    user = request.user
    
    if request.GET.get('remove_avatar') == '1' and user.avatar:
        user.avatar.delete(save=False)
        user.save()
        messages.success(request, 'Profile picture removed.')
        return redirect('settings')
    
    if request.method == 'POST' and request.FILES.get('avatar'):
        avatar_file = request.FILES.get('avatar')
        crop_x = request.POST.get('crop_x', '0')
        crop_y = request.POST.get('crop_y', '0')
        crop_size = request.POST.get('crop_size', '50')
        
        if avatar_file.content_type.startswith('image/'):
            img = Image.open(avatar_file)
            
            target_size = (400, 400)
            img_ratio = img.width / img.height
            
            if img_ratio > 1:
                new_height = target_size[1]
                new_width = int(new_height * img_ratio)
            else:
                new_width = target_size[0]
                new_height = int(new_width / img_ratio)
            
            img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
            
            try:
                offset_x_percent = float(crop_x)
                offset_y_percent = float(crop_y)
                size_percent = float(crop_size)
                
                offset_x_px = int((offset_x_percent / 100) * new_width)
                offset_y_px = int((offset_y_percent / 100) * new_height)
                
                crop_px = int((size_percent / 100) * new_width)
                crop_px = max(50, min(crop_px, min(new_width, new_height)))
            except (ValueError, ZeroDivisionError):
                offset_x_px = 0
                offset_y_px = 0
                crop_px = target_size[0]
            
            left = max(0, offset_x_px)
            top = max(0, offset_y_px)
            right = min(new_width, left + crop_px)
            bottom = min(new_height, top + crop_px)
            
            if right - left < crop_px:
                left = max(0, right - crop_px)
            if bottom - top < crop_px:
                top = max(0, bottom - crop_px)
            
            img = img.crop((left, top, right, bottom))
            
            if img.width != target_size[0] or img.height != target_size[1]:
                img = img.resize(target_size, Image.Resampling.LANCZOS)
            
            output = io.BytesIO()
            img.save(output, format='PNG', quality=90)
            output.seek(0)
            
            if user.avatar:
                user.avatar.delete(save=False)
            user.avatar = InMemoryUploadedFile(
                output,
                'avatar',
                f'{user.username}_avatar.png',
                'image/png',
                output.getbuffer().nbytes,
                None
            )
            user.save()
            messages.success(request, 'Profile picture updated successfully!')
            return redirect('settings')
        else:
            messages.error(request, 'Please upload a valid image file.')
    
    if request.method == 'POST':
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Password updated successfully!')
            return redirect('settings')
    else:
        form = PasswordChangeForm(request.user)
    
    context = {'form': form}
    return render(request, 'settings.html', context)


@login_required
def import_export(request):
    contacts_count = Contact.objects.filter(workspace=request.user.workspace, is_deleted=False).count()
    context = {'contacts_count': contacts_count}
    return render(request, 'import_export.html', context)


def buttons(request):
    return render(request, 'buttons.html')