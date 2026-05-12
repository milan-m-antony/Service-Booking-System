from django import forms
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.password_validation import validate_password
from django.utils import timezone
from django.utils.text import slugify

from .models import Booking, BookingFeedback, CustomUser, Service, StaffBlockedSlot, StaffLeaveDate


class RegisterForm(forms.ModelForm):
    first_name = forms.CharField(required=True)
    last_name = forms.CharField(required=False)
    email = forms.EmailField(required=True)
    phone = forms.CharField(required=False)
    password1 = forms.CharField(widget=forms.PasswordInput(), label="Password")

    class Meta:
        model = CustomUser
        fields = ("first_name", "last_name", "email", "phone", "password1")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        placeholder_map = {
            "first_name": "Enter first name",
            "last_name": "Enter last name",
            "email": "Enter email",
            "phone": "Enter phone number",
            "password1": "Create a password",
        }
        self.fields["first_name"].label = "First Name"
        self.fields["last_name"].label = "Last Name"
        for name, field in self.fields.items():
            field.widget.attrs.update({"class": "form-control"})
            if name in placeholder_map:
                field.widget.attrs["placeholder"] = placeholder_map[name]

    def clean_password1(self):
        password = self.cleaned_data.get("password1", "")
        validate_password(password, self.instance)
        return password

    def save(self, commit=True):
        user = super().save(commit=False)
        user.first_name = self.cleaned_data["first_name"].strip()
        user.last_name = self.cleaned_data.get("last_name", "").strip()
        user.email = self.cleaned_data["email"]
        user.phone = self.cleaned_data.get("phone", "")
        user.role = CustomUser.Roles.CUSTOMER
        user.set_password(self.cleaned_data["password1"])
        base_username = slugify(" ".join(filter(None, [user.first_name, user.last_name]))) or slugify(user.email.split("@")[0]) or "user"
        candidate = base_username
        suffix = 1
        while CustomUser.objects.filter(username=candidate).exclude(pk=user.pk).exists():
            candidate = f"{base_username}{suffix}"
            suffix += 1
        user.username = candidate
        if commit:
            user.save()
        return user


class LoginForm(AuthenticationForm):
    username = forms.CharField(widget=forms.TextInput(attrs={"placeholder": "Enter email, username, or full name", "autofocus": True}))
    password = forms.CharField(widget=forms.PasswordInput(attrs={"placeholder": "Enter password"}))

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.update({"class": "form-control"})

    def clean(self):
        username_value = self.cleaned_data.get("username")
        print(f"Cleaning LoginForm. Username: {username_value}")
        if username_value:
            match = None
            if "@" in username_value:
                print("Checking email match")
                match = CustomUser.objects.filter(email__iexact=username_value).first()
            else:
                print("Checking username match")
                match = CustomUser.objects.filter(username__iexact=username_value).first()
                if not match:
                    print("Checking full name match")
                    first_name, _, last_name = username_value.partition(" ")
                    if first_name:
                        query = CustomUser.objects.filter(first_name__iexact=first_name)
                        if last_name.strip():
                            query = query.filter(last_name__iexact=last_name.strip())
                        if query.count() == 1:
                            match = query.first()
            if match:
                print(f"Match found: {match.username}")
                self.cleaned_data["username"] = match.username
            else:
                print("No match found")
        return super().clean()


class ProfileForm(forms.ModelForm):
    class Meta:
        model = CustomUser
        fields = ("first_name", "last_name", "email", "phone", "avatar")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["first_name"].label = "First Name"
        self.fields["last_name"].label = "Last Name"
        self.fields["first_name"].widget.attrs.update({"class": "form-control", "placeholder": "Enter first name"})
        self.fields["last_name"].widget.attrs.update({"class": "form-control", "placeholder": "Enter last name"})
        self.fields["email"].widget.attrs.update({"class": "form-control"})
        self.fields["phone"].widget.attrs.update({"class": "form-control"})
        self.fields["avatar"].widget = forms.FileInput(attrs={"class": "form-control", "accept": "image/*"})


class BookingForm(forms.ModelForm):
    customer = forms.ModelChoiceField(
        queryset=CustomUser.objects.filter(role=CustomUser.Roles.CUSTOMER),
        required=False,
    )

    class Meta:
        model = Booking
        fields = ("customer", "service", "staff", "scheduled_at", "address", "location_coords", "notes")
        widgets = {
            "scheduled_at": forms.DateTimeInput(attrs={"type": "datetime-local"}),
            "address": forms.Textarea(attrs={"rows": 2, "placeholder": "Flat/House No, Building, Landmark..."}),
            "location_coords": forms.HiddenInput(),
            "notes": forms.Textarea(attrs={"rows": 3, "placeholder": "Any specific request or extra details?"}),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)
        self.fields["service"].queryset = Service.objects.filter(is_active=True)
        self.fields["staff"].queryset = CustomUser.objects.filter(role=CustomUser.Roles.STAFF)
        self.fields["service"].empty_label = "Select a service"
        self.fields["staff"].empty_label = "Select professional"

        if not (self.user and self.user.role == CustomUser.Roles.ADMIN):
            if "customer" in self.fields:
                self.fields.pop("customer")
        else:
            if "customer" in self.fields:
                self.fields["customer"].empty_label = "Select customer"

        for field in self.fields.values():
            css_class = "form-control"
            if isinstance(field.widget, forms.Select):
                css_class = "form-select"
            field.widget.attrs.update({"class": css_class})

    def clean(self):
        cleaned_data = super().clean()
        service = cleaned_data.get("service")
        if service and service.staff.count() == 0:
            raise forms.ValidationError("This service currently has no professionals assigned and cannot be booked.")
        return cleaned_data

    def clean_scheduled_at(self):
        scheduled_at = self.cleaned_data["scheduled_at"]
        if scheduled_at <= timezone.now():
            raise forms.ValidationError("Please choose a future date and time.")

        staff = self.cleaned_data.get("staff")
        if staff and StaffLeaveDate.objects.filter(staff=staff, date=scheduled_at.date(), is_active=True).exists():
            raise forms.ValidationError("Selected date is unavailable for this professional. Please pick another date.")

        if staff and StaffBlockedSlot.objects.filter(
            staff=staff,
            date=scheduled_at.date(),
            time=scheduled_at.time().replace(second=0, microsecond=0),
            is_active=True,
        ).exists():
            raise forms.ValidationError("Selected time slot is unavailable for this professional. Please pick another slot.")
        return scheduled_at


class BookingFeedbackForm(forms.ModelForm):
    class Meta:
        model = BookingFeedback
        fields = ("rating", "comment")
        widgets = {
            "comment": forms.Textarea(attrs={"rows": 4, "placeholder": "Share what went well or what should improve"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["rating"].widget.attrs.update({"class": "form-select"})
        self.fields["comment"].widget.attrs.update({"class": "form-control"})
