from django.shortcuts import render, redirect
from django.contrib import messages

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
# 1. QUẢN LÝ TÀI KHOẢN (ĐĂNG NHẬP & ĐĂNG KÝ)
# ==========================================
def login_view(request):
    """
    Xử lý giao diện và đăng nhập người dùng.
    """
    if request.method == "POST":
        # TODO: Xử lý authenticate(username=..., password=...) và login(request, user)
        username = request.POST.get("username")
        messages.success(request, f"Đăng nhập thành công! Xin chào {username}.")
        return redirect("rescue_create")
    return render(request, "accounts/login.html")


def register_view(request):
    """
    Xử lý giao diện và đăng ký tài khoản mới.
    """
    if request.method == "POST":
        # TODO: Lưu tài khoản mới vào database User/Rescuer profile
        full_name = request.POST.get("full_name")
        messages.success(request, f"Tài khoản của {full_name} đã được tạo thành công! Hãy đăng nhập.")
        return redirect("login")
    return render(request, "accounts/register.html")


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
