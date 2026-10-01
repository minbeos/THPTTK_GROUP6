from django.urls import path
from . import views

urlpatterns = [
    # 0. Trang chủ trước khi đăng nhập
    path("", views.landing_view, name="landing"),

    # 1. Quản lý tài khoản
    path("login/", views.login_view, name="login"),
    path("register/", views.register_view, name="register"),

    # 2. Tạo yêu cầu cứu hộ khẩn cấp
    path("rescue/create/", views.create_request_view, name="rescue_create"),

    # 3. Trao đổi & Chấp nhận hỗ trợ
    path("rescue/support-chat/", views.support_chat_view, name="support_chat"),

    # 4. Theo dõi vị trí thời gian thực
    path("rescue/tracking/", views.live_tracking_view, name="live_tracking"),

    # 5. Đánh giá sao và nhận xét
    path("rescue/rating/", views.rating_feedback_view, name="rating_feedback"),
]
