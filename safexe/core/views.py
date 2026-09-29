from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth import login, logout
from .forms import RegisterForm, LoginForm
from .models import User

# ==========================================
# 0. TRANG CHỦ (HOMEPAGE)
# ==========================================
def home_view(request):
    """
    Hiển thị giao diện trang chủ với form đăng nhập và đăng ký.
    Xử lý trực tiếp form tại trang chủ mà không chuyển hướng.
    """
    if request.user.is_authenticated:
        return redirect("live_tracking")

    context = {
        "active_tab": "login",
        "login_data": {},
        "register_data": {},
    }

    if request.method == "POST":
        action = request.POST.get("action")
        
        if action == "login":
            context["active_tab"] = "login"
            context["login_data"] = request.POST
            form = LoginForm(request.POST)
            if form.is_valid():
                user = form.cleaned_data['user']
                login(request, user, backend='django.contrib.auth.backends.ModelBackend')
                if form.cleaned_data.get("remember_me"):
                    request.session.set_expiry(1209600)
                else:
                    request.session.set_expiry(0)
                messages.success(request, f"Đăng nhập thành công! Chào mừng {user.full_name or user.phone}.")
                return redirect("live_tracking")
            else:
                for field, errors in form.errors.items():
                    for error in errors:
                        messages.error(request, f"{error}")
        
        elif action == "register":
            context["active_tab"] = "register"
            context["register_data"] = request.POST
            form = RegisterForm(request.POST)
            if form.is_valid():
                try:
                    user = form.save()
                    messages.success(request, "Đăng ký thành công! Vui lòng đăng nhập để tiếp tục.")
                    context["active_tab"] = "login"
                    context["register_data"] = {}
                except Exception as e:
                    messages.error(request, f"Đã xảy ra lỗi hệ thống: {e}")
            else:
                for field, errors in form.errors.items():
                    for error in errors:
                        messages.error(request, f"{error}")

    return render(request, "home.html", context)

# ==========================================
# 1. QUẢN LÝ TÀI KHOẢN (ĐĂNG NHẬP & ĐĂNG KÝ)
# ==========================================
def login_view(request):
    """
    Xử lý giao diện và xác thực đăng nhập tài khoản (Use Case 02).
    Post-condition: Chuyển hướng đến màn hình chia sẻ vị trí GPS (live_tracking).
    """
    if request.user.is_authenticated:
        return redirect("live_tracking")

    if request.method == "POST":
        form = LoginForm(request.POST)
        if form.is_valid():
            user = form.cleaned_data['user']
            login(request, user, backend='django.contrib.auth.backends.ModelBackend')

            # Cấu hình lưu phiên ghi nhớ đăng nhập
            if form.cleaned_data.get("remember_me"):
                request.session.set_expiry(1209600)  # 14 ngày
            else:
                request.session.set_expiry(0)  # Đóng trình duyệt sẽ hủy session

            messages.success(request, f"Đăng nhập thành công! Chào mừng {user.full_name or user.phone} đến với SafeXe.")
            next_url = request.GET.get("next") or "live_tracking"
            return redirect(next_url)
        else:
            messages.error(request, "Đăng nhập không thành công. Vui lòng kiểm tra lại thông tin!")
    else:
        form = LoginForm()

    return render(request, "accounts/login.html", {"form": form})


def logout_view(request):
    """
    Đăng xuất người dùng khỏi hệ thống.
    """
    logout(request)
    messages.info(request, "Bạn đã đăng xuất thành công.")
    return redirect("login")



def register_view(request):
    """
    Xử lý giao diện và đăng ký tài khoản mới (Use Case 01).
    """
    if request.user.is_authenticated:
        return redirect("rescue_create")

    if request.method == "POST":
        form = RegisterForm(request.POST)
        if form.is_valid():
            try:
                user = form.save()
                messages.success(request, "Đăng ký tài khoản thành công! Vui lòng đăng nhập để tiếp tục.")
                return redirect("login")
            except Exception as e:
                messages.error(request, f"Đã xảy ra lỗi hệ thống khi lưu tài khoản. Vui lòng thử lại! Lỗi: {e}")
        else:
            messages.error(request, "Đăng ký không thành công. Vui lòng kiểm tra và sửa lại các trường bị lỗi.")
    else:
        form = RegisterForm()

    return render(request, "accounts/register.html", {"form": form})


def google_login_simulate_view(request):
    """
    Giả lập đăng nhập bằng Google (Dùng cho demo đồ án).
    """
    email = "google_user_demo@gmail.com"
    phone = "0999888777"
    cccd = "000111222333"
    
    user, created = User.objects.get_or_create(
        email=email,
        defaults={
            "username": phone,
            "phone": phone,
            "cccd": cccd,
            "full_name": "Google User Demo",
            "role": "user"
        }
    )
    if created:
        user.set_password("demo123456")
        user.save()
        
    login(request, user, backend='social_core.backends.google.GoogleOAuth2')
    messages.success(request, f"Đăng nhập qua Google thành công! Chào mừng {user.full_name}.")
    return redirect("live_tracking")

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
