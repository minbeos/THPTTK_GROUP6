from django.urls import path
from . import views

urlpatterns = [
    # 1. Quản lý tài khoản & Chuyển đổi vai trò kiểm thử
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
    path("register/", views.register_view, name="register"),
    path("switch-user/<str:username>/", views.switch_user_view, name="switch_user"),

    # 2. Tạo yêu cầu cứu hộ khẩn cấp (Người gặp nạn)
    path("", views.create_request_view, name="rescue_create"),
    path("rescue/create/", views.create_request_view, name="rescue_create_alt"),

    # 3. Tiếp nhận yêu cầu cứu hộ (Người cứu hộ / Thợ)
    path("rescuer/", views.rescuer_dashboard_view, name="rescuer_dashboard"),
    path("rescue/detail/<int:request_id>/", views.request_detail_view, name="request_detail"),
    path("rescue/accept/<int:request_id>/", views.accept_request_view, name="accept_request"),
    path("rescue/reject/<int:request_id>/", views.reject_request_view, name="reject_request"),
    path("rescuer/toggle-status/", views.toggle_rescuer_status_view, name="toggle_rescuer_status"),

    # 4. Trao đổi & Thống nhất phương án (Chat)
    path("rescue/support-chat/", views.support_chat_view, name="support_chat"),

    # 5. Theo dõi vị trí thời gian thực & Bản đồ dẫn đường (Live GPS Tracking)
    path("rescue/tracking/", views.live_tracking_view, name="live_tracking"),
    path("rescue/update-status/<int:request_id>/", views.update_request_status_view, name="update_request_status"),

    # 6. Đánh giá chất lượng dịch vụ
    path("rescue/rating/", views.rating_feedback_view, name="rating_feedback"),

    # 7. API Polling thời gian thực
    path("api/request-status/<int:request_id>/", views.api_request_status, name="api_request_status"),
]
