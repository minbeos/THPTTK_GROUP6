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
from core.models import UserProfile
from django.contrib.messages import get_messages

def run_tests():
    print("==================================================")
    print(" BẮT ĐẦU KIỂM THỬ USE CASE: CHỈNH SỬA HỒ SƠ (UC-PROFILE-01)")
    print("==================================================")

    client = Client()

    # Test 1: Pre-condition - Người dùng chưa đăng nhập truy cập /profile/edit/
    resp = client.get('/profile/edit/')
    assert resp.status_code == 302 and '/login/' in resp.url, f"Test 1 Failed: {resp.status_code}, {resp.url}"
    print("[PASS] Test 1 (Pre-condition): Người dùng chưa đăng nhập bị chuyển hướng đến trang Login.")

    # Khởi tạo user kiểm thử
    phone_init = "0933445566"
    cccd_init = "079201001122"
    pwd = "Password@123"
    User.objects.filter(username__in=[phone_init, "0933445577"]).delete()
    User.objects.filter(email__in=["test_profile@safexe.vn", "new_email_profile@safexe.vn"]).delete()
    UserProfile.objects.filter(phone__in=[phone_init, "0933445577"]).delete()
    UserProfile.objects.filter(id_card__in=[cccd_init, "079201009999"]).delete()

    user = User.objects.create_user(
        username=phone_init,
        email="test_profile@safexe.vn",
        password=pwd,
        first_name="Nguyễn Văn Ban Đầu"
    )
    UserProfile.objects.create(
        user=user,
        phone=phone_init,
        id_card=cccd_init,
        role="user"
    )

    # Đăng nhập
    login_success = client.login(username=phone_init, password=pwd)
    assert login_success, "Đăng nhập user kiểm thử thất bại!"
    print("[PASS] Đăng nhập tài khoản kiểm thử thành công.")

    # Test 2: Main flow bước 1 - 4 - Truy cập giao diện chỉnh sửa hồ sơ
    resp = client.get('/profile/edit/')
    assert resp.status_code == 200, f"Test 2 Failed: Status {resp.status_code}"
    content = resp.content.decode('utf-8')
    assert "Chỉnh Sửa Hồ Sơ" in content and "Họ và tên" in content and "Số CCCD" in content
    assert "Nguyễn Văn Ban Đầu" in content and phone_init in content and cccd_init in content
    print("[PASS] Test 2: Giao diện hiển thị đầy đủ thông tin hiện tại (Họ tên, SĐT, CCCD, Email).")

    # Test 3: Exception flow 7a - Bỏ trống trường bắt buộc
    resp = client.post('/profile/edit/', {
        'full_name': '',
        'phone': phone_init,
        'cccd': cccd_init,
        'email': 'valid@safexe.vn'
    })
    messages = [m.message for m in get_messages(resp.wsgi_request)]
    assert any("Vui lòng nhập đầy đủ" in m for m in messages), f"Test 3 Failed: {messages}"
    print("[PASS] Test 3 (Exception 7a): Báo lỗi khi bỏ trống trường bắt buộc.")

    # Test 4: Exception flow 7a - Định dạng SĐT hoặc CCCD sai
    resp = client.post('/profile/edit/', {
        'full_name': 'Nguyễn Văn Đã Đổi',
        'phone': '093344', # SĐT thiếu số
        'cccd': cccd_init,
        'email': 'valid@safexe.vn'
    })
    messages = [m.message for m in get_messages(resp.wsgi_request)]
    assert any("Số điện thoại phải gồm đúng 10 chữ số" in m for m in messages), f"Test 4 Failed: {messages}"
    print("[PASS] Test 4 (Exception 7a): Báo lỗi khi SĐT không đúng 10 chữ số.")

    # Test 5: Exception flow 7a - Định dạng email sai
    resp = client.post('/profile/edit/', {
        'full_name': 'Nguyễn Văn Đã Đổi',
        'phone': phone_init,
        'cccd': cccd_init,
        'email': 'email_khong_hop_le'
    })
    messages = [m.message for m in get_messages(resp.wsgi_request)]
    assert any("Định dạng email không hợp lệ" in m for m in messages), f"Test 5 Failed: {messages}"
    print("[PASS] Test 5 (Exception 7a): Báo lỗi khi nhập email sai định dạng.")

    # Test 6: Alternative flow 6a - Người dùng không thay đổi thông tin nào
    resp = client.post('/profile/edit/', {
        'full_name': 'Nguyễn Văn Ban Đầu',
        'phone': phone_init,
        'cccd': cccd_init,
        'email': 'test_profile@safexe.vn'
    })
    assert resp.status_code == 302 and '/account/' in resp.url, f"Test 6 Failed: {resp.status_code}, {resp.url}"
    messages = [m.message for m in get_messages(resp.wsgi_request)]
    assert any("Không có thông tin nào thay đổi" in m for m in messages), f"Test 6 Failed: {messages}"
    print("[PASS] Test 6 (Alternative 6a): Hệ thống giữ nguyên thông tin khi không có thay đổi.")

    # Test 7: Main flow bước 5-9 & Alternative flow 5a - Cập nhật tất cả các trường thành công
    new_phone = "0933445577"
    new_cccd = "079201009999"
    resp = client.post('/profile/edit/', {
        'full_name': 'Nguyễn Văn Mới Cập Nhật',
        'phone': new_phone,
        'cccd': new_cccd,
        'email': 'new_email_profile@safexe.vn'
    })
    assert resp.status_code == 302 and '/account/' in resp.url, f"Test 7 Failed: {resp.status_code}"
    messages = [m.message for m in get_messages(resp.wsgi_request)]
    assert any("Cập nhật thông tin thành công" in m for m in messages), f"Test 7 Failed: {messages}"
    print("[PASS] Test 7 (Main flow): Hệ thống lưu thông tin mới (Họ tên, SĐT, CCCD, Email) và thông báo thành công.")

    # Test 8: Post-condition - Kiểm tra dữ liệu mới nhất được đồng bộ trong database và giao diện Tài khoản
    user.refresh_from_db()
    assert user.first_name == "Nguyễn Văn Mới Cập Nhật"
    assert user.email == "new_email_profile@safexe.vn"
    assert user.profile.phone == new_phone
    assert user.profile.id_card == new_cccd

    resp_account = client.get('/account/')
    assert resp_account.status_code == 200
    account_content = resp_account.content.decode('utf-8')
    assert "Nguyễn Văn Mới Cập Nhật" in account_content
    assert new_phone in account_content
    assert new_cccd in account_content
    assert "new_email_profile@safexe.vn" in account_content
    print("[PASS] Test 8 (Post-condition): Thông tin hồ sơ mới nhất (CCCD, SĐT, Email) hiển thị chính xác trên trang Tài khoản.")

    print("==================================================")
    print(" TẤT CẢ CÁC BƯỚC KIỂM THỬ USE CASE UC-PROFILE-01 ĐÃ ĐẠT 100%!")
    print("==================================================")

if __name__ == '__main__':
    run_tests()
