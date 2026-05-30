from django.shortcuts import render, redirect
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
    contacts = Contact.objects.filter(workspace=request.user.workspace, is_deleted=False)[:5]
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
            created_by=request.user
        )
        messages.success(request, 'Contact created successfully!')
        return redirect('contacts')
    
    return render(request, 'contacts/create.html')


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
            
            # Calculate crop offset based on user selection
            try:
                offset_x_percent = float(crop_x)
                offset_y_percent = float(crop_y)
                
                offset_x_px = int((offset_x_percent / 100) * (new_width - target_size[0]))
                offset_y_px = int((offset_y_percent / 100) * (new_height - target_size[1]))
            except (ValueError, ZeroDivisionError):
                offset_x_px = 0
                offset_y_px = 0
            
            # Center crop with user offset
            left = max(0, (new_width - target_size[0]) // 2 + offset_x_px)
            top = max(0, (new_height - target_size[1]) // 2 + offset_y_px)
            right = min(new_width, left + target_size[0])
            bottom = min(new_height, top + target_size[1])
            
            # Ensure we have a valid crop area
            if right - left < target_size[0]:
                left = max(0, right - target_size[0])
            if bottom - top < target_size[1]:
                top = max(0, bottom - target_size[1])
            
            img = img.crop((left, top, right, bottom))
            
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


def buttons(request):
    return render(request, 'buttons.html')