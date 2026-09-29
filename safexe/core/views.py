import re
from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from .models import UserProfile
# ==========================================
# 0. TRANG CHỦ TRƯỚC KHI ĐĂNG NHẬP (LANDING PAGE)
# ==========================================
def landing_view(request):
    """
    Trang chủ giới thiệu SafeXe trước khi đăng nhập.
    Tích hợp thông tin mạng lưới P2P 10km và form đăng nhập/đăng ký.
    """
    return render(request, "landing.html")
# ==========================================
# 1. QUẢN LÝ TÀI KHOẢN (ĐĂNG NHẬP, ĐĂNG KÝ, ĐỔI MẬT KHẨU, HỒ SƠ)
# ==========================================
def login_view(request):
    """
    Xử lý giao diện và đăng nhập người dùng thực tế với Django Auth.
    """
    if request.user.is_authenticated:
        return redirect("rescue_create")

    # Tạo tài khoản demo nếu chưa tồn tại
    if not User.objects.filter(username="demo").exists():
        demo_u = User.objects.create_user(
            username="demo",
            email="demo@safexe.vn",
            password="Password@123",
            first_name="Nguyễn Văn Demo"
        )
        UserProfile.objects.get_or_create(
            user=demo_u,
            defaults={"phone": "0912345678", "id_card": "001201012345", "role": "user"}
        )

    if request.method == "POST":
        account = request.POST.get("username", "").strip()
        password = request.POST.get("password", "")

        # Cho phép đăng nhập bằng username, email hoặc số điện thoại
        user = authenticate(request, username=account, password=password)
        if user is None:
            # Thử tìm theo email
            try:
                user_obj = User.objects.get(email=account)
                user = authenticate(request, username=user_obj.username, password=password)
            except (User.DoesNotExist, User.MultipleObjectsReturned):
                user = None
        if user is None:
            # Thử tìm theo số điện thoại trong UserProfile
            try:
                profile_obj = UserProfile.objects.get(phone=account)
                user = authenticate(request, username=profile_obj.user.username, password=password)
            except (UserProfile.DoesNotExist, UserProfile.MultipleObjectsReturned):
                user = None

        if user is not None:
            login(request, user)
            messages.success(request, f"Đăng nhập thành công! Xin chào {user.first_name or user.username}.")
            next_url = request.GET.get("next") or "rescue_create"
            return redirect(next_url)
        else:
            messages.error(request, "Tài khoản hoặc mật khẩu không chính xác. Vui lòng thử lại!")

    return render(request, "accounts/login.html")


def register_view(request):
    """
    USE CASE: ĐĂNG KÝ TÀI KHOẢN (UC-01) - Thư
    
    - Pre-conditions: Người dùng chưa đăng nhập hệ thống. Hệ thống có thể kết nối với cơ sở dữ liệu.
    - Main flow:
        1. Người dùng truy cập màn hình 'Đăng ký'.
        2. Hệ thống hiển thị biểu mẫu gồm: Họ và tên, Số điện thoại, Email, CCCD, Mật khẩu và Xác nhận mật khẩu.
        3. Người dùng nhập đầy đủ thông tin đăng ký.
        4. Người dùng nhấn nút 'Đăng ký'.
        5. Hệ thống kiểm tra tính hợp lệ và kiểm tra trùng lặp thông tin.
        6. Nếu thông tin hợp lệ, hệ thống lưu thông tin người dùng vào cơ sở dữ liệu.
        7. Hệ thống hiển thị thông báo 'Đăng ký thành công.'
        8. Hệ thống chuyển hướng đến màn hình đăng nhập.
        
    - Business rules:
        - Tất cả trường đăng ký đều bắt buộc nhập.
        - Số điện thoại: 10 số (bắt đầu bằng 0), không trùng dữ liệu.
        - CCCD: 12 số, không trùng dữ liệu.
        - Email: đúng định dạng, không trùng.
        - Mật khẩu: ≥ 8 ký tự, có chữ và số, không có khoảng trắng.
        - Mật khẩu xác nhận phải khớp.
    """
    if request.user.is_authenticated:
        return redirect("rescue_create")

    if request.method == "POST":
        full_name = request.POST.get("full_name", "").strip()
        phone = request.POST.get("phone", "").strip()
        cccd = request.POST.get("cccd", "").strip()
        email = request.POST.get("email", "").strip()
        password = request.POST.get("password", "")
        confirm_password = request.POST.get("confirm_password", "")
        role = request.POST.get("role", "user")

        form_context = {
            "full_name": full_name,
            "phone": phone,
            "cccd": cccd,
            "email": email,
            "role": role,
        }

        # 1. Tất cả trường đăng ký đều bắt buộc nhập
        if not full_name or not phone or not cccd or not email or not password or not confirm_password:
            messages.error(request, "Vui lòng nhập đầy đủ tất cả các trường thông tin bắt buộc.")
            return render(request, "accounts/register.html", form_context)

        # 2. Số điện thoại 10 số (bắt đầu bằng 0)
        if not re.match(r"^0\d{9}$", phone):
            messages.error(request, "Số điện thoại phải gồm đúng 10 chữ số (bắt đầu bằng số 0).")
            return render(request, "accounts/register.html", form_context)

        # 3. CCCD 12 số
        if not re.match(r"^\d{12}$", cccd):
            messages.error(request, "Số CCCD phải gồm đúng 12 chữ số.")
            return render(request, "accounts/register.html", form_context)

        # 4. Email đúng định dạng
        if not re.match(r"^[\w\.-]+@[\w\.-]+\.\w+$", email):
            messages.error(request, "Địa chỉ email không đúng định dạng. Vui lòng kiểm tra lại.")
            return render(request, "accounts/register.html", form_context)

        # 5. Mật khẩu >= 8 ký tự, có chữ và số, không có khoảng trắng
        if len(password) < 8 or not re.search(r"[A-Za-z]", password) or not re.search(r"\d", password) or " " in password:
            messages.error(request, "Mật khẩu phải có tối thiểu 8 ký tự, gồm cả chữ và số, không chứa khoảng trắng.")
            return render(request, "accounts/register.html", form_context)

        # 6. Mật khẩu xác nhận trùng khớp
        if password != confirm_password:
            messages.error(request, "Mật khẩu xác nhận không khớp.")
            return render(request, "accounts/register.html", form_context)

        # 7. Kiểm tra trùng lặp thông tin
        if User.objects.filter(username=phone).exists() or UserProfile.objects.filter(phone=phone).exists():
            messages.error(request, "Số điện thoại này đã được đăng ký trên hệ thống.")
            return render(request, "accounts/register.html", form_context)

        if User.objects.filter(email=email).exists():
            messages.error(request, "Địa chỉ email này đã được sử dụng bởi một tài khoản khác.")
            return render(request, "accounts/register.html", form_context)

        if UserProfile.objects.filter(id_card=cccd).exists():
            messages.error(request, "Số CCCD này đã được sử dụng bởi một tài khoản khác.")
            return render(request, "accounts/register.html", form_context)

        # 8. Lưu thông tin người dùng vào cơ sở dữ liệu
        try:
            user = User.objects.create_user(
                username=phone,
                email=email,
                password=password,
                first_name=full_name
            )
            UserProfile.objects.create(
                user=user,
                phone=phone,
                id_card=cccd,
                role=role
            )
            messages.success(request, "Đăng ký thành công.")
            return redirect("login")
        except Exception:
            messages.error(request, "Đăng ký thất bại. Đã có lỗi xảy ra khi lưu tài khoản, vui lòng thử lại.")
            return render(request, "accounts/register.html", form_context)

    return render(request, "accounts/register.html")


def logout_view(request):
    """
    Đăng xuất người dùng khỏi hệ thống và chuyển về trang đăng nhập.
    """
    logout(request)
    messages.info(request, "Bạn đã đăng xuất an toàn.")
    return redirect("login")


@login_required(login_url='login')
def account_view(request):
    """
    Quản lý thông tin tài khoản và trung tâm bảo mật SafeXe.
    Hiển thị thông tin người dùng và điều hướng đến Đổi mật khẩu / Chỉnh sửa hồ sơ.
    """
    profile, _ = UserProfile.objects.get_or_create(
        user=request.user,
        defaults={"phone": request.user.username, "id_card": "", "role": "user"}
    )
    return render(request, "accounts/account.html", {
        "user": request.user,
        "profile": profile
    })


@login_required(login_url='login')
def edit_profile_view(request):
    """
    USE CASE: CHỈNH SỬA HỒ SƠ CÁ NHÂN (UC-PROFILE-01) - Nguyệt
    Cập nhật được các trường: Họ và tên, Số điện thoại, Email, CCCD.
    
    - Pre-conditions: Người dùng đã đăng nhập hệ thống.
    - Main flow:
        1. Người dùng truy cập chức năng Hồ sơ cá nhân.
        2. Hệ thống hiển thị thông tin hồ sơ hiện tại của người dùng.
        3. Người dùng chọn Chỉnh sửa.
        4. Hệ thống hiển thị giao diện chỉnh sửa thông tin cá nhân.
        5. Người dùng cập nhật thông tin cá nhân (Họ tên, SĐT, Email, CCCD).
        6. Người dùng chọn Lưu.
        7. Hệ thống kiểm tra tính hợp lệ của thông tin được cập nhật.
        8. Nếu thông tin hợp lệ, hệ thống lưu thông tin mới.
        9. Hệ thống thông báo 'Cập nhật thông tin thành công.' và hiển thị thông tin hồ sơ mới.
    """
    user = request.user
    profile, _ = UserProfile.objects.get_or_create(
        user=user,
        defaults={"phone": user.username, "id_card": "", "role": "user"}
    )

    if request.method == "POST":
        full_name = request.POST.get("full_name", "").strip()
        phone = request.POST.get("phone", "").strip()
        cccd = request.POST.get("cccd", "").strip()
        email = request.POST.get("email", "").strip()

        form_context = {
            "full_name": full_name,
            "phone": phone,
            "cccd": cccd,
            "email": email,
        }

        # Exception flow 7a: Kiểm tra dữ liệu hợp lệ
        # 1. Tất cả các trường bắt buộc nhập
        if not full_name or not phone or not cccd or not email:
            messages.error(request, "Vui lòng nhập đầy đủ tất cả các trường thông tin bắt buộc.")
            return render(request, "accounts/edit_profile.html", form_context)

        # 2. Số điện thoại: 10 chữ số (bắt đầu bằng 0)
        if not re.match(r"^0\d{9}$", phone):
            messages.error(request, "Số điện thoại phải gồm đúng 10 chữ số (bắt đầu bằng số 0).")
            return render(request, "accounts/edit_profile.html", form_context)

        # 3. CCCD: 12 chữ số
        if not re.match(r"^\d{12}$", cccd):
            messages.error(request, "Số CCCD phải gồm đúng 12 chữ số.")
            return render(request, "accounts/edit_profile.html", form_context)

        # 4. Định dạng email hợp lệ
        if not re.match(r"^[\w\.-]+@[\w\.-]+\.\w+$", email):
            messages.error(request, "Định dạng email không hợp lệ. Vui lòng kiểm tra lại.")
            return render(request, "accounts/edit_profile.html", form_context)

        # 5. Kiểm tra trùng lặp với tài khoản khác
        if UserProfile.objects.filter(phone=phone).exclude(user=user).exists() or \
           User.objects.filter(username=phone).exclude(id=user.id).exists():
            messages.error(request, "Số điện thoại này đã được sử dụng bởi một tài khoản khác.")
            return render(request, "accounts/edit_profile.html", form_context)

        if User.objects.filter(email=email).exclude(id=user.id).exists():
            messages.error(request, "Email này đã được sử dụng bởi một tài khoản khác.")
            return render(request, "accounts/edit_profile.html", form_context)

        if UserProfile.objects.filter(id_card=cccd).exclude(user=user).exists():
            messages.error(request, "Số CCCD này đã được sử dụng bởi một tài khoản khác.")
            return render(request, "accounts/edit_profile.html", form_context)

        # Alternative flow 6a: Nếu người dùng không thay đổi thông tin nào
        current_phone = profile.phone or user.username
        current_cccd = profile.id_card or ""
        if full_name == (user.first_name or "") and email == (user.email or "") and phone == current_phone and cccd == current_cccd:
            messages.info(request, "Không có thông tin nào thay đổi. Thông tin hồ sơ được giữ nguyên.")
            return redirect("account")

        # Main flow bước 8: Hệ thống lưu thông tin mới
        try:
            user.first_name = full_name
            user.email = email
            user.username = phone
            user.save()

            profile.phone = phone
            profile.id_card = cccd
            profile.save()

            # Main flow bước 9: Thông báo thành công
            messages.success(request, "Cập nhật thông tin thành công.")
            return redirect("account")
        except Exception:
            messages.error(request, "Đã có lỗi xảy ra khi lưu thông tin. Vui lòng thử lại.")
            return render(request, "accounts/edit_profile.html", form_context)

    # GET request: Hiển thị giao diện với dữ liệu hiện tại
    return render(request, "accounts/edit_profile.html", {
        "full_name": user.first_name,
        "phone": profile.phone or user.username,
        "cccd": profile.id_card or "",
        "email": user.email,
    })


@login_required(login_url='login')
def change_password_view(request):
    """
    USE CASE: ĐỔI MẬT KHẨU (UC-AUTH-03)
    
    - Pre-conditions: Người dùng đã đăng nhập hệ thống.
    - Main flow:
        1. Người dùng truy cập chức năng Đổi mật khẩu.
        2. Hệ thống hiển thị các trường: Mật khẩu hiện tại, Mật khẩu mới, Xác nhận mật khẩu mới.
        3. Người dùng nhập mật khẩu hiện tại.
        4. Người dùng nhập mật khẩu mới và xác nhận mật khẩu mới.
        5. Người dùng chọn Đổi mật khẩu.
        6. Hệ thống kiểm tra tính hợp lệ của thông tin được nhập.
        7. Hệ thống xác thực mật khẩu hiện tại.
        8. Nếu thông tin hợp lệ, hệ thống cập nhật mật khẩu mới.
        9. Hệ thống thông báo: 'Đổi mật khẩu thành công.'
        
    - Alternative flows:
        4a. Người dùng có thể hủy thao tác đổi mật khẩu trước khi xác nhận. (Nút Quay lại/Hủy).
        
    - Exception flows:
        6a. Bỏ trống một trong các trường: 'Vui lòng nhập đầy đủ thông tin.'
        6b. Mật khẩu mới không đáp ứng yêu cầu bảo mật: 'Mật khẩu mới phải có tối thiểu 8 ký tự, bao gồm cả chữ và số.'
        7a. Mật khẩu hiện tại không chính xác: 'Mật khẩu hiện tại không chính xác.'
        7b. Mật khẩu mới và mật khẩu xác nhận không trùng khớp: 'Mật khẩu xác nhận không khớp.'
        7c. Mật khẩu mới trùng với mật khẩu hiện tại: 'Mật khẩu mới phải khác mật khẩu hiện tại.'
        8a. Lỗi cập nhật hệ thống: 'Không thể đổi mật khẩu, vui lòng thử lại.'
    """
    if request.method == "POST":
        old_password = request.POST.get("old_password", "")
        new_password = request.POST.get("new_password", "")
        confirm_password = request.POST.get("confirm_password", "")

        # Exception flow 6a: Bỏ trống một trong các trường bắt buộc
        if not old_password or not new_password or not confirm_password:
            messages.error(request, "Vui lòng nhập đầy đủ thông tin.")
            return render(request, "accounts/change_password.html")

        # Exception flow 7a: Mật khẩu hiện tại không chính xác
        if not request.user.check_password(old_password):
            messages.error(request, "Mật khẩu hiện tại không chính xác.")
            return render(request, "accounts/change_password.html")

        # Exception flow 7c: Mật khẩu mới trùng với mật khẩu hiện tại
        if old_password == new_password or request.user.check_password(new_password):
            messages.error(request, "Mật khẩu mới phải khác mật khẩu hiện tại.")
            return render(request, "accounts/change_password.html")

        # Exception flow 7b: Mật khẩu mới và mật khẩu xác nhận không trùng khớp
        if new_password != confirm_password:
            messages.error(request, "Mật khẩu xác nhận không khớp.")
            return render(request, "accounts/change_password.html")

        # Exception flow 6b: Mật khẩu mới không đáp ứng yêu cầu bảo mật (tối thiểu 8 ký tự, gồm cả chữ và số)
        if len(new_password) < 8 or not re.search(r'[A-Za-z]', new_password) or not re.search(r'[0-9]', new_password):
            messages.error(request, "Mật khẩu mới phải có tối thiểu 8 ký tự, bao gồm cả chữ và số.")
            return render(request, "accounts/change_password.html")

        # Main flow bước 8: Cập nhật mật khẩu mới
        try:
            user = request.user
            user.set_password(new_password)
            user.save()

            # Giữ phiên đăng nhập cho người dùng sau khi đổi mật khẩu
            update_session_auth_hash(request, user)

            # Main flow bước 9: Thông báo thành công
            messages.success(request, "Đổi mật khẩu thành công.")
            return redirect("change_password")
        except Exception as e:
            # Exception flow 8a: Nếu xảy ra lỗi trong quá trình cập nhật
            messages.error(request, "Không thể đổi mật khẩu, vui lòng thử lại.")
            return render(request, "accounts/change_password.html")

    return render(request, "accounts/change_password.html")



# ==========================================
# 2. TẠO YÊU CẦU CỨU HỘ KHẨN CẤP (SOS)
# ==========================================
def create_request_view(request):
    """
    Gửi tín hiệu cứu hộ khẩn cấp và lưu vị trí GPS.
    """
    if request.method == "POST":
        # TODO: Lưu yêu cầu cứu hộ vào RescueRequest model
        messages.success(request, "Tín hiệu cứu hộ khẩn cấp đã được phát đi thành công! Đang quét thợ gần nhất...")
        return redirect("support_chat")
    return render(request, "rescue/create_request.html")


# ==========================================
# 3. TRAO ĐỔI & CHẤP NHẬN HỖ TRỢ (CHAT)
# ==========================================
def support_chat_view(request):
    """
    Giao diện nhắn tin trao đổi giữa thợ và người cần cứu hộ,
    đồng thời cho phép chấp nhận hoặc từ chối đề xuất hỗ trợ.
    """
    if request.method == "POST":
        action = request.POST.get("action")
        if action == "accept":
            messages.success(request, "Bạn đã chấp nhận hỗ trợ! Thợ cứu hộ đang bắt đầu di chuyển.")
            return redirect("live_tracking")
        elif action == "reject":
            messages.info(request, "Đã hủy đề xuất. Đang tiếp tục tìm kiếm người hỗ trợ khác.")
            return redirect("rescue_create")

    # Dữ liệu mẫu (Mock data) truyền sang template
    context = {
        "rescue_id": "SX-8921",
        "rescue_status": "Đã ghép nối thợ cứu hộ",
        "location_address": "120 Hoàng Minh Thảo, P. Hòa Khánh Nam, Liên Chiểu, Đà Nẵng",
        "helper_name": "Nguyễn Văn Hùng",
        "helper_phone": "0905123456",
        "proposed_fee": "50.000 VNĐ",
    }
    return render(request, "support/chat_and_accept.html", context)


# ==========================================
# 4. THEO DÕI VỊ TRÍ THỜI GIAN THỰC (LIVE GPS)
# ==========================================
def live_tracking_view(request):
    """
    Theo dõi lộ trình di chuyển của người hỗ trợ tới vị trí sự cố.
    """
    context = {
        "rescue_id": "SX-8921",
        "eta_minutes": 5,
        "distance_km": 1.2,
        "helper_name": "Nguyễn Văn Hùng",
        "helper_vehicle": "Wave Alpha đỏ - 43C1 123.45",
    }
    return render(request, "tracking/live_tracking.html", context)


# ==========================================
# 5. ĐÁNH GIÁ SAO & GỬI NHẬN XÉT DỊCH VỤ
# ==========================================
def rating_feedback_view(request):
    """
    Chấm điểm sao, chọn tiêu chí và gửi phản hồi chất lượng phục vụ.
    """
    if request.method == "POST":
        score = request.POST.get("rating_score", "5")
        comment = request.POST.get("comment", "")
        # TODO: Lưu Review/Feedback vào database
        messages.success(request, f"Cảm ơn bạn đã đánh giá {score} sao! Chúc bạn thượng lộ bình an.")
        return redirect("rescue_create")

    context = {
        "rescue_id": "SX-8921",
        "helper_name": "Nguyễn Văn Hùng",
    }
    return render(request, "reviews/rating_feedback.html", context)
