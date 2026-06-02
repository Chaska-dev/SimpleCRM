from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth.forms import PasswordChangeForm
from django.core.files.uploadedfile import InMemoryUploadedFile
from django.http import JsonResponse
from .forms import UserRegistrationForm, LoginForm
from .models import Contact, Company, Country, State, City
import io


def get_or_create_company(workspace, company_name):
    if not company_name or not company_name.strip():
        return None
    company, _ = Company.objects.get_or_create(
        workspace=workspace,
        name__iexact=company_name.strip(),
        defaults={'name': company_name.strip()}
    )
    return company


def get_or_create_country(name):
    if not name or not name.strip():
        return None
    name = name.strip()
    country = Country.objects.filter(name_es__iexact=name).first()
    if country:
        return country
    country = Country.objects.filter(name_en__iexact=name).first()
    if country:
        return country
    return Country.objects.create(name_es=name, name_en=name, code=name[:3].upper())


def get_or_create_state(country, name):
    if not name or not name.strip():
        return None
    name = name.strip()
    state = State.objects.filter(country=country, name_es__iexact=name).first()
    if state:
        return state
    state = State.objects.filter(country=country, name_en__iexact=name).first()
    if state:
        return state
    return State.objects.create(country=country, name_es=name, name_en=name, code=name[:3].upper())


def get_or_create_city(state, name):
    if not name or not name.strip():
        return None
    name = name.strip()
    city = City.objects.filter(state=state, name_es__iexact=name).first()
    if city:
        return city
    city = City.objects.filter(state=state, name_en__iexact=name).first()
    if city:
        return city
    return City.objects.create(state=state, name_es=name, name_en=name)


@login_required
def company_search(request):
    query = request.GET.get('q', '')
    if query:
        companies = Company.objects.filter(
            workspace=request.user.workspace,
            name__icontains=query,
            is_deleted=False
        ).values('id', 'name')[:10]
    else:
        companies = Company.objects.filter(
            workspace=request.user.workspace,
            is_deleted=False
        ).values('id', 'name')[:10]
    return JsonResponse(list(companies), safe=False)


@login_required
def companies(request):
    companies = Company.objects.filter(workspace=request.user.workspace, is_deleted=False)
    context = {'companies': companies}
    return render(request, 'companies/list.html', context)


@login_required
def company_create(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        legal_name = request.POST.get('legal_name', '')
        website = request.POST.get('website', '')
        industry = request.POST.get('industry', '')
        phone = request.POST.get('phone', '')
        email = request.POST.get('email', '')
        address = request.POST.get('address', '')
        description = request.POST.get('description', '')

        logo_file = request.FILES.get('logo')
        cropped_logo = None

        if logo_file and logo_file.content_type.startswith('image/'):
            from PIL import Image
            import io

            img = Image.open(logo_file)

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

            cropped_logo = InMemoryUploadedFile(
                output,
                'logo',
                f'company_logo.png',
                'image/png',
                output.getbuffer().nbytes,
                None
            )

        company = Company.objects.create(
            workspace=request.user.workspace,
            name=name,
            legal_name=legal_name,
            website=website,
            industry=industry,
            phone=phone,
            email=email,
            address=address,
            description=description,
            logo=cropped_logo,
            created_by=request.user
        )
        messages.success(request, 'Company created successfully!')
        return redirect('companies')

    return render(request, 'companies/create.html')


@login_required
def company_edit(request, company_uuid):
    company = get_object_or_404(Company, uuid=company_uuid, workspace=request.user.workspace, is_deleted=False)

    if request.method == 'POST':
        company.name = request.POST.get('name', company.name)
        company.legal_name = request.POST.get('legal_name', '')
        company.website = request.POST.get('website', '')
        company.industry = request.POST.get('industry', '')
        company.phone = request.POST.get('phone', '')
        company.email = request.POST.get('email', '')
        company.address = request.POST.get('address', '')
        company.description = request.POST.get('description', '')

        logo_file = request.FILES.get('logo')
        if logo_file and logo_file.content_type.startswith('image/'):
            from PIL import Image
            import io

            img = Image.open(logo_file)

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

            if company.logo:
                company.logo.delete(save=False)
            company.logo = InMemoryUploadedFile(
                output,
                'logo',
                f'company_logo.png',
                'image/png',
                output.getbuffer().nbytes,
                None
            )

        company.save()
        messages.success(request, 'Company updated successfully!')
        return redirect('companies')

    context = {'company': company}
    return render(request, 'companies/edit.html', context)


@login_required
def company_delete(request, company_uuid):
    company = get_object_or_404(Company, uuid=company_uuid, workspace=request.user.workspace, is_deleted=False)
    company.is_deleted = True
    company.save()
    messages.success(request, 'Company deleted successfully!')
    return redirect('companies')


@login_required
def company_bulk_delete(request):
    uuids = request.GET.getlist('uuids')
    if uuids:
        Company.objects.filter(uuid__in=uuids, workspace=request.user.workspace, is_deleted=False).update(is_deleted=True)
        messages.success(request, f'{len(uuids)} company(s) deleted successfully!')
    else:
        messages.error(request, 'No companies selected.')
    return redirect('companies')


@login_required
def country_search(request):
    query = request.GET.get('q', '')
    lang = request.GET.get('lang', 'es')
    name_field = 'name_en' if lang == 'en' else 'name_es'
    if query:
        countries = Country.objects.filter(**{f'{name_field}__icontains': query}).values('id', name_field)[:15]
    else:
        countries = Country.objects.values('id', name_field)[:15]
    result = [{'id': c['id'], 'name': c[name_field]} for c in countries]
    return JsonResponse(result, safe=False)


@login_required
def state_search(request):
    country_id = request.GET.get('country', '')
    query = request.GET.get('q', '')
    lang = request.GET.get('lang', 'es')
    name_field = 'name_en' if lang == 'en' else 'name_es'
    if country_id:
        states = State.objects.filter(country_id=country_id)
        if query:
            states = states.filter(**{f'{name_field}__icontains': query})
        states = states.values('id', name_field)[:15]
    elif query:
        states = State.objects.filter(**{f'{name_field}__icontains': query}).values('id', name_field)[:15]
    else:
        states = State.objects.values('id', name_field)[:15]
    result = [{'id': s['id'], 'name': s[name_field]} for s in states]
    return JsonResponse(result, safe=False)


@login_required
def city_search(request):
    state_id = request.GET.get('state', '')
    query = request.GET.get('q', '')
    lang = request.GET.get('lang', 'es')
    name_field = 'name_en' if lang == 'en' else 'name_es'
    if state_id:
        cities = City.objects.filter(state_id=state_id)
        if query:
            cities = cities.filter(**{f'{name_field}__icontains': query})
        cities = cities.values('id', name_field)[:15]
    elif query:
        cities = City.objects.filter(**{f'{name_field}__icontains': query}).values('id', name_field)[:15]
    else:
        cities = City.objects.values('id', name_field)[:15]
    result = [{'id': c['id'], 'name': c[name_field]} for c in cities]
    return JsonResponse(result, safe=False)


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
        company_name = request.POST.get('company', '')
        company = get_or_create_company(request.user.workspace, company_name)
        website = request.POST.get('website', '')
        address = request.POST.get('address', '')

        country_id = request.POST.get('country_id', '')
        country_name = request.POST.get('country', '')
        if country_id.isdigit():
            country_obj = Country.objects.filter(id=country_id).first()
        else:
            country_obj = get_or_create_country(country_name)

        state_id = request.POST.get('state_id', '')
        state_name = request.POST.get('state', '')
        if state_id.isdigit() and country_obj:
            state_obj = State.objects.filter(id=state_id, country=country_obj).first()
        else:
            state_obj = get_or_create_state(country_obj, state_name) if country_obj else None

        city_id = request.POST.get('city_id', '')
        city_name = request.POST.get('city', '')
        if city_id.isdigit() and state_obj:
            city_obj = City.objects.filter(id=city_id, state=state_obj).first()
        else:
            city_obj = get_or_create_city(state_obj, city_name) if state_obj else None
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
            company=company,
            website=website,
            address=address,
            country=country_obj,
            state=state_obj,
            city=city_obj,
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
        company_name = request.POST.get('company', '')
        contact.company = get_or_create_company(request.user.workspace, company_name)
        contact.website = request.POST.get('website', '')
        contact.address = request.POST.get('address', '')

        country_id = request.POST.get('country_id', '')
        country_name = request.POST.get('country', '')
        if country_id.isdigit():
            contact.country = Country.objects.filter(id=country_id).first()
        else:
            contact.country = get_or_create_country(country_name)

        state_id = request.POST.get('state_id', '')
        state_name = request.POST.get('state', '')
        if state_id.isdigit() and contact.country:
            contact.state = State.objects.filter(id=state_id, country=contact.country).first()
        else:
            contact.state = get_or_create_state(contact.country, state_name) if contact.country else None

        city_id = request.POST.get('city_id', '')
        city_name = request.POST.get('city', '')
        if city_id.isdigit() and contact.state:
            contact.city = City.objects.filter(id=city_id, state=contact.state).first()
        else:
            contact.city = get_or_create_city(contact.state, city_name) if contact.state else None

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
        messages.success(request, 'Contact created successfully!')
        
        if request.POST.get('from_dashboard'):
            return redirect('dashboard')
        
        return redirect('contacts')
    
    context = {'contact': contact, 'custom_social_profiles_json': contact.custom_social_profiles}
    return render(request, 'contacts/edit.html', context)


@login_required
def contact_delete(request, contact_uuid):
    contact = get_object_or_404(Contact, uuid=contact_uuid, workspace=request.user.workspace, is_deleted=False)
    contact.is_deleted = True
    contact.save()
    messages.success(request, 'Contact deleted successfully!')
    return redirect('contacts')


@login_required
def contact_bulk_delete(request):
    uuids = request.GET.getlist('uuids')
    if uuids:
        Contact.objects.filter(uuid__in=uuids, workspace=request.user.workspace, is_deleted=False).update(is_deleted=True)
        messages.success(request, f'{len(uuids)} contact(s) deleted successfully!')
    else:
        messages.error(request, 'No contacts selected.')
    return redirect('contacts')


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