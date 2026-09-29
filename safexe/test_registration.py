import os
import sys
import django

sys.stdout.reconfigure(encoding='utf-8')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
django.setup()

from core.forms import RegisterForm
from core.models import User

def test_register():
    # Clear existing users for fresh test
    User.objects.all().delete()

    print("--- 1. Testing Valid Registration ---")
    data_valid = {
        'role': 'user',
        'full_name': 'Nguyễn Văn A',
        'phone': '0905123456',
        'cccd': '123456789012',
        'email': 'nguyenvana@example.com',
        'password': 'Password123',
        'confirm_password': 'Password123'
    }
    form = RegisterForm(data_valid)
    assert form.is_valid(), f"Form should be valid, errors: {form.errors}"
    user = form.save()
    print(f"[OK] User created successfully: ID={user.id}, Phone={user.phone}, Role={user.role}")
    assert user.check_password('Password123'), "Password should be hashed securely!"
    print("[OK] Password successfully hashed and checked!")

    print("\n--- 2. Testing Duplicate Phone Validation ---")
    data_dup_phone = data_valid.copy()
    data_dup_phone['cccd'] = '987654321098'
    data_dup_phone['email'] = 'other@example.com'
    form_dup = RegisterForm(data_dup_phone)
    assert not form_dup.is_valid(), "Form should be invalid due to duplicate phone"
    print(f"[OK] Duplicate phone blocked: {form_dup.errors.get('phone').as_text()}")

    print("\n--- 3. Testing Duplicate CCCD Validation ---")
    data_dup_cccd = data_valid.copy()
    data_dup_cccd['phone'] = '0909999999'
    data_dup_cccd['email'] = 'cccd@example.com'
    form_dup_cccd = RegisterForm(data_dup_cccd)
    assert not form_dup_cccd.is_valid(), "Form should be invalid due to duplicate CCCD"
    print(f"[OK] Duplicate CCCD blocked: {form_dup_cccd.errors.get('cccd').as_text()}")

    print("\n--- 4. Testing Password Weakness (No numbers) ---")
    data_weak_pwd = data_valid.copy()
    data_weak_pwd['phone'] = '0911111111'
    data_weak_pwd['cccd'] = '111111111111'
    data_weak_pwd['email'] = 'weak@example.com'
    data_weak_pwd['password'] = 'OnlyLetters'
    data_weak_pwd['confirm_password'] = 'OnlyLetters'
    form_weak = RegisterForm(data_weak_pwd)
    assert not form_weak.is_valid(), "Form should be invalid due to password rules"
    print(f"[OK] Weak password blocked: {form_weak.errors.get('password').as_text()}")

    print("\n--- 5. Testing Password Mismatch ---")
    data_mismatch = data_valid.copy()
    data_mismatch['phone'] = '0922222222'
    data_mismatch['cccd'] = '222222222222'
    data_mismatch['email'] = 'mismatch@example.com'
    data_mismatch['password'] = 'Password123'
    data_mismatch['confirm_password'] = 'Password999'
    form_mismatch = RegisterForm(data_mismatch)
    assert not form_mismatch.is_valid(), "Form should be invalid due to password mismatch"
    print(f"[OK] Password mismatch blocked: {form_mismatch.errors.get('confirm_password').as_text()}")

    print("\n--- ALL REGISTRATION TESTS PASSED PERFECTLY! ---")

if __name__ == '__main__':
    test_register()
