import os
import sys
import django

if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'settings')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
django.setup()

from django.test import Client
from django.contrib.auth.models import User
from django.contrib.auth import authenticate
from django.contrib.messages import get_messages

def run_tests():
    print("==================================================")
    print(" BẮT ĐẦU KIỂM THỬ USE CASE: ĐỔI MẬT KHẨU (UC-AUTH-03)")
    print("==================================================")

    # Khởi tạo user kiểm thử
    username = "test_user_pttk"
    initial_pwd = "OldPassword@123"
    User.objects.filter(username=username).delete()
    user = User.objects.create_user(username=username, password=initial_pwd, first_name="Nguyễn Văn Test")

    client = Client()

    # Test 1: Pre-condition - Người dùng chưa đăng nhập truy cập Đổi mật khẩu
    resp = client.get('/change-password/')
    assert resp.status_code == 302 and '/login/' in resp.url, f"Test 1 Failed: {resp.status_code}, {resp.url}"
    print("[PASS] Test 1: Người dùng chưa đăng nhập bị chuyển hướng đến trang Login.")

    # Đăng nhập
    login_success = client.login(username=username, password=initial_pwd)
    assert login_success, "Đăng nhập test user thất bại!"
    print("[PASS] Đăng nhập tài khoản test thành công.")

    # Test 2: Main flow bước 1 & 2 - Truy cập giao diện Đổi mật khẩu
    resp = client.get('/change-password/')
    assert resp.status_code == 200, f"Test 2 Failed: Status {resp.status_code}"
    content = resp.content.decode('utf-8')
    assert "Mật khẩu hiện tại" in content and "Mật khẩu mới" in content and "Xác nhận mật khẩu mới" in content
    print("[PASS] Test 2: Giao diện hiển thị đầy đủ 3 trường theo đúng Main flow.")

    # Test 3: Exception flow 6a - Bỏ trống trường bắt buộc
    resp = client.post('/change-password/', {
        'old_password': '',
        'new_password': 'NewPassword@456',
        'confirm_password': 'NewPassword@456'
    })
    messages = [m.message for m in get_messages(resp.wsgi_request)]
    assert "Vui lòng nhập đầy đủ thông tin." in messages, f"Test 3 Failed: Messages: {messages}"
    print("[PASS] Test 3 (Exception 6a): Báo lỗi 'Vui lòng nhập đầy đủ thông tin.' khi để trống.")

    # Test 4: Exception flow 7a - Mật khẩu hiện tại không chính xác
    resp = client.post('/change-password/', {
        'old_password': 'WrongPassword123',
        'new_password': 'NewPassword@456',
        'confirm_password': 'NewPassword@456'
    })
    messages = [m.message for m in get_messages(resp.wsgi_request)]
    assert "Mật khẩu hiện tại không chính xác." in messages, f"Test 4 Failed: Messages: {messages}"
    print("[PASS] Test 4 (Exception 7a): Báo lỗi 'Mật khẩu hiện tại không chính xác.' khi nhập sai MK cũ.")

    # Test 5: Exception flow 7c - Mật khẩu mới trùng mật khẩu hiện tại
    resp = client.post('/change-password/', {
        'old_password': initial_pwd,
        'new_password': initial_pwd,
        'confirm_password': initial_pwd
    })
    messages = [m.message for m in get_messages(resp.wsgi_request)]
    assert "Mật khẩu mới phải khác mật khẩu hiện tại." in messages, f"Test 5 Failed: Messages: {messages}"
    print("[PASS] Test 5 (Exception 7c): Báo lỗi 'Mật khẩu mới phải khác mật khẩu hiện tại.' khi trùng MK cũ.")

    # Test 6: Exception flow 7b - Mật khẩu mới và xác nhận không khớp
    resp = client.post('/change-password/', {
        'old_password': initial_pwd,
        'new_password': 'NewPassword@456',
        'confirm_password': 'MismatchPassword@456'
    })
    messages = [m.message for m in get_messages(resp.wsgi_request)]
    assert "Mật khẩu xác nhận không khớp." in messages, f"Test 6 Failed: Messages: {messages}"
    print("[PASS] Test 6 (Exception 7b): Báo lỗi 'Mật khẩu xác nhận không khớp.' khi 2 mật khẩu khác nhau.")

    # Test 7: Exception flow 6b - Mật khẩu mới không đáp ứng yêu cầu bảo mật (< 8 ký tự hoặc thiếu số/chữ)
    resp = client.post('/change-password/', {
        'old_password': initial_pwd,
        'new_password': 'short',
        'confirm_password': 'short'
    })
    messages = [m.message for m in get_messages(resp.wsgi_request)]
    assert any("Mật khẩu mới phải có tối thiểu 8 ký tự" in m for m in messages), f"Test 7 Failed: Messages: {messages}"
    print("[PASS] Test 7 (Exception 6b): Báo lỗi yêu cầu bảo mật khi mật khẩu mới không đạt chuẩn.")

    # Test 8: Main flow - Đổi mật khẩu thành công
    new_pwd = "NewPassword@2026"
    resp = client.post('/change-password/', {
        'old_password': initial_pwd,
        'new_password': new_pwd,
        'confirm_password': new_pwd
    }, follow=True)
    messages = [m.message for m in get_messages(resp.wsgi_request)]
    assert "Đổi mật khẩu thành công." in messages, f"Test 8 Failed: Messages: {messages}"
    print("[PASS] Test 8 (Main flow): Hệ thống cập nhật mật khẩu mới và thông báo 'Đổi mật khẩu thành công.'")

    # Test 9: Post-condition - Xác thực mật khẩu mới và mật khẩu cũ
    auth_old = authenticate(username=username, password=initial_pwd)
    auth_new = authenticate(username=username, password=new_pwd)
    assert auth_old is None, "Test 9 Failed: Mật khẩu cũ vẫn còn hiệu lực!"
    assert auth_new is not None, "Test 9 Failed: Mật khẩu mới không đăng nhập được!"
    print("[PASS] Test 9 (Post-condition): Mật khẩu mới hoạt động chính xác, mật khẩu cũ bị vô hiệu.")

    print("==================================================")
    print(" TẤT CẢ CÁC BƯỚC KIỂM THỬ USE CASE ĐÃ ĐẠT 100%!")
    print("==================================================")

if __name__ == "__main__":
    run_tests()
