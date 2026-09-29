import re
from django import forms
from django.core.exceptions import ValidationError
from django.core.validators import EmailValidator
from .models import User

class RegisterForm(forms.Form):
    ROLE_CHOICES = (
        ('user', 'Chủ phương tiện'),
        ('rescuer', 'Thợ cứu hộ'),
    )
    
    role = forms.ChoiceField(
        choices=ROLE_CHOICES,
        initial='user',
        required=True,
        error_messages={'required': 'Vui lòng chọn vai trò sử dụng.'}
    )
    full_name = forms.CharField(
        max_length=150,
        required=True,
        error_messages={
            'required': 'Họ và tên không được để trống.',
            'max_length': 'Họ và tên không quá 150 ký tự.'
        }
    )
    phone = forms.CharField(
        max_length=10,
        required=True,
        error_messages={
            'required': 'Số điện thoại không được để trống.',
            'max_length': 'Số điện thoại phải đúng 10 chữ số.'
        }
    )
    cccd = forms.CharField(
        max_length=12,
        required=True,
        error_messages={
            'required': 'Căn cước công dân (CCCD) không được để trống.',
            'max_length': 'CCCD phải đúng 12 chữ số.'
        }
    )
    email = forms.EmailField(
        required=True,
        validators=[EmailValidator(message='Địa chỉ email không đúng định dạng.')],
        error_messages={
            'required': 'Địa chỉ email không được để trống.',
            'invalid': 'Địa chỉ email không đúng định dạng.'
        }
    )
    password = forms.CharField(
        widget=forms.PasswordInput(),
        required=True,
        error_messages={'required': 'Mật khẩu không được để trống.'}
    )
    confirm_password = forms.CharField(
        widget=forms.PasswordInput(),
        required=True,
        error_messages={'required': 'Mật khẩu xác nhận không được để trống.'}
    )

    def clean_phone(self):
        phone = self.cleaned_data.get('phone', '').strip()
        if not re.match(r'^\d{10}$', phone):
            raise ValidationError('Số điện thoại phải bao gồm đúng 10 chữ số.')
        if User.objects.filter(phone=phone).exists():
            raise ValidationError('Số điện thoại này đã được đăng ký trên hệ thống.')
        return phone

    def clean_cccd(self):
        cccd = self.cleaned_data.get('cccd', '').strip()
        if not re.match(r'^\d{12}$', cccd):
            raise ValidationError('Số CCCD phải bao gồm đúng 12 chữ số.')
        if User.objects.filter(cccd=cccd).exists():
            raise ValidationError('Số CCCD này đã được đăng ký trên hệ thống.')
        return cccd

    def clean_email(self):
        email = self.cleaned_data.get('email', '').strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise ValidationError('Địa chỉ email này đã được sử dụng.')
        return email

    def clean_password(self):
        password = self.cleaned_data.get('password', '')
        if len(password) < 8:
            raise ValidationError('Mật khẩu phải có độ dài tối thiểu 8 ký tự.')
        if ' ' in password:
            raise ValidationError('Mật khẩu không được chứa khoảng trắng.')
        if not (re.search(r'[A-Za-z]', password) and re.search(r'\d', password)):
            raise ValidationError('Mật khẩu phải chứa cả chữ cái và chữ số.')
        return password

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get('password')
        confirm_password = cleaned_data.get('confirm_password')

        if password and confirm_password and password != confirm_password:
            self.add_error('confirm_password', 'Mật khẩu xác nhận không trùng khớp!')

        return cleaned_data

    def save(self):
        cleaned_data = self.cleaned_data
        phone = cleaned_data['phone']
        email = cleaned_data['email']
        password = cleaned_data['password']
        full_name = cleaned_data['full_name']
        cccd = cleaned_data['cccd']
        role = cleaned_data['role']

        # Dùng phone làm username để đảm bảo duy nhất trong Django Auth
        user = User.objects.create_user(
            username=phone,
            phone=phone,
            email=email,
            password=password,
            full_name=full_name,
            cccd=cccd,
            role=role
        )
        return user


class LoginForm(forms.Form):
    username = forms.CharField(
        required=False,
        error_messages={'required': 'Vui lòng nhập số điện thoại/email.'}
    )
    password = forms.CharField(
        widget=forms.PasswordInput(),
        required=False,
        error_messages={'required': 'Vui lòng nhập mật khẩu.'}
    )
    remember_me = forms.BooleanField(required=False)

    def clean(self):
        cleaned_data = super().clean()
        username = (cleaned_data.get('username') or '').strip()
        password = cleaned_data.get('password') or ''

        # Exception flow 5b: Nếu số điện thoại/email để trống
        if not username:
            self.add_error('username', 'Vui lòng nhập số điện thoại/email.')

        # Exception flow 5c: Nếu mật khẩu để trống
        if not password:
            self.add_error('password', 'Vui lòng nhập mật khẩu.')

        if not username or not password:
            return cleaned_data

        # Tìm kiếm tài khoản qua SĐT, Username hoặc Email
        user = (
            User.objects.filter(phone=username).first() or 
            User.objects.filter(username=username).first() or 
            User.objects.filter(email__iexact=username).first()
        )

        # Exception flow 7a: Nếu số điện thoại/email không tồn tại
        if not user:
            self.add_error('username', 'Số điện thoại/Email không chính xác.')
            return cleaned_data

        # Exception flow 7b: Nếu mật khẩu không đúng
        if not user.check_password(password):
            self.add_error('password', 'Mật khẩu không chính xác.')
            return cleaned_data

        # Tài khoản không hoạt động
        if not user.is_active:
            self.add_error('username', 'Tài khoản của bạn đã bị khóa hoặc không được cấp quyền.')
            return cleaned_data

        cleaned_data['user'] = user
        return cleaned_data

