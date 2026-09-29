import os
import sys
import django

sys.stdout.reconfigure(encoding='utf-8')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
django.setup()

from django.test import Client
from core.models import User
from core.forms import LoginForm

def test_login_use_case():
    print("=== START TESTING USE CASE 02: ĐĂNG NHẬP TÀI KHOẢN ===")
    
    # Reset test database
    User.objects.all().delete()
    
    # Tạo sẵn user thử nghiệm
    user = User.objects.create_user(
        username='0905123456',
        phone='0905123456',
        email='nguyenvana@gmail.com',
        password='Password123',
        full_name='Nguyễn Văn A',
        cccd='123456789012',
        role='user'
    )
    print(f"[PRE-CONDITION OK] Created test user: Phone={user.phone}, Email={user.email}")

    # 1. Test Exception 5b: Số điện thoại/Email để trống
    print("\n--- 1. Testing Exception 5b: Empty Phone/Email ---")
    form_5b = LoginForm({'username': '', 'password': 'Password123'})
    assert not form_5b.is_valid(), "Form should be invalid when username is empty"
    err_5b = form_5b.errors.get('username')[0]
    print(f"[OK] Blocked empty username: {err_5b}")
    assert err_5b == 'Vui lòng nhập số điện thoại/email.', f"Unexpected error message: {err_5b}"

    # 2. Test Exception 5c: Mật khẩu để trống
    print("\n--- 2. Testing Exception 5c: Empty Password ---")
    form_5c = LoginForm({'username': '0905123456', 'password': ''})
    assert not form_5c.is_valid(), "Form should be invalid when password is empty"
    err_5c = form_5c.errors.get('password')[0]
    print(f"[OK] Blocked empty password: {err_5c}")
    assert err_5c == 'Vui lòng nhập mật khẩu.', f"Unexpected error message: {err_5c}"

    # 3. Test Exception 7a: Số điện thoại/Email không tồn tại
    print("\n--- 3. Testing Exception 7a: Non-existent Phone/Email ---")
    form_7a = LoginForm({'username': '0999999999', 'password': 'Password123'})
    assert not form_7a.is_valid(), "Form should be invalid when user does not exist"
    err_7a = form_7a.errors.get('username')[0]
    print(f"[OK] Blocked non-existent account: {err_7a}")
    assert err_7a == 'Số điện thoại/Email không chính xác.', f"Unexpected error message: {err_7a}"

    # 4. Test Exception 7b: Mật khẩu không đúng
    print("\n--- 4. Testing Exception 7b: Incorrect Password ---")
    form_7b = LoginForm({'username': '0905123456', 'password': 'WrongPassword999'})
    assert not form_7b.is_valid(), "Form should be invalid when password is wrong"
    err_7b = form_7b.errors.get('password')[0]
    print(f"[OK] Blocked incorrect password: {err_7b}")
    assert err_7b == 'Mật khẩu không chính xác.', f"Unexpected error message: {err_7b}"

    # 5. Test Main Flow: Đăng nhập bằng SĐT thành công
    print("\n--- 5. Testing Main Flow: Valid Login via Phone ---")
    form_valid_phone = LoginForm({'username': '0905123456', 'password': 'Password123'})
    assert form_valid_phone.is_valid(), f"Form should be valid. Errors: {form_valid_phone.errors}"
    assert form_valid_phone.cleaned_data['user'] == user, "Authenticated user does not match"
    print("[OK] LoginForm verified successfully for Phone login!")

    # 6. Test Main Flow: Đăng nhập bằng Email thành công
    print("\n--- 6. Testing Main Flow: Valid Login via Email ---")
    form_valid_email = LoginForm({'username': 'nguyenvana@gmail.com', 'password': 'Password123'})
    assert form_valid_email.is_valid(), f"Form should be valid via email. Errors: {form_valid_email.errors}"
    assert form_valid_email.cleaned_data['user'] == user, "Authenticated user does not match"
    print("[OK] LoginForm verified successfully for Email login!")

    # 7. Test Integration & Redirect to Live Tracking (Post-Condition)
    print("\n--- 7. Testing Django Client HTTP POST & Post-Condition Redirect ---")
    client = Client()
    response = client.post('/login/', {'username': '0905123456', 'password': 'Password123'}, follow=True)
    assert response.status_code == 200, f"Response code should be 200 after redirect, got {response.status_code}"
    # Check redirect path (Post condition: live_tracking)
    redirect_chain = response.redirect_chain
    print(f"[OK] Redirect Chain: {redirect_chain}")
    assert redirect_chain and '/rescue/tracking/' in redirect_chain[0][0], "Should redirect to live_tracking (/rescue/tracking/)"
    assert '_auth_user_id' in client.session, "Session should be created for logged in user"
    print("[OK] Post-condition verified: User session created and redirected to live tracking (GPS)!")

    # 8. Test Logout Business Rule
    print("\n--- 8. Testing Logout Business Rule ---")
    logout_res = client.get('/logout/', follow=True)
    assert '_auth_user_id' not in client.session, "Session should be flushed on logout"
    print("[OK] Logout successfully flushed session!")

    print("\n🎉 ALL TEST CASES FOR USE CASE 02 PASSED 100% PERFECTLY! 🎉")

if __name__ == '__main__':
    test_login_use_case()
