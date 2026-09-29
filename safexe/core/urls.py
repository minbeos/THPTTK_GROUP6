from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    # 1. Quản lý tài khoản
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
    path("register/", views.register_view, name="register"),

    # Password Reset
    path('password_reset/', auth_views.PasswordResetView.as_view(), name='password_reset'),
    path('password_reset/done/', auth_views.PasswordResetDoneView.as_view(), name='password_reset_done'),
    path('reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(), name='password_reset_confirm'),
    path('reset/done/', auth_views.PasswordResetCompleteView.as_view(), name='password_reset_complete'),

    # 2. Tạo yêu cầu cứu hộ khẩn cấp
    path("", views.home_view, name="home"),
    path("rescue/create/", views.create_request_view, name="rescue_create"),

    # 3. Trao đổi & Chấp nhận hỗ trợ
    path("rescue/support-chat/", views.support_chat_view, name="support_chat"),

    # 4. Theo dõi vị trí thời gian thực
    path("rescue/tracking/", views.live_tracking_view, name="live_tracking"),

    # 5. Đánh giá sao và nhận xét
    path("rescue/rating/", views.rating_feedback_view, name="rating_feedback"),
]
