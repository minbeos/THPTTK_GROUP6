import os
import math
import random
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages, auth
from django.contrib.auth.models import User
from django.db import transaction
from django.http import JsonResponse
from django.views.decorators.http import require_POST

from .models import (
    UserProfile,
    RescueRequest,
    RescueResponseLog,
    ChatMessage,
    Notification,
    calculate_distance_km,
)


def get_current_user(request):
    """
    Hàm tiện ích lấy người dùng hiện tại.
    Nếu chưa đăng nhập, tự động lấy user mẫu 'nan_nhan' để người dùng thử nghiệm mượt mà.
    """
    if request.user.is_authenticated:
        return request.user
    
    # Kiểm tra session chọn demo user
    username = request.session.get('demo_username', 'nan_nhan')
    user = User.objects.filter(username=username).first()
    if not user:
        user = User.objects.first()
    if user:
        # Tự động đăng nhập vào session
        auth.login(request, user, backend='django.contrib.auth.backends.ModelBackend')
        return user
    return None


def switch_user_view(request, username):
    """
    Chức năng chuyển đổi nhanh giữa các tài khoản thử nghiệm:
    - 'nan_nhan': Người gặp nạn (Lê Thị Mai)
    - 'tho_hung': Thợ cứu hộ 1 (Nguyễn Văn Hùng - Sẵn sàng, cách 1.2km)
    - 'tho_long': Thợ cứu hộ 2 (Trần Văn Long - Sẵn sàng, cách 3.8km)
    """
    user = User.objects.filter(username=username).first()
    if user:
        auth.login(request, user, backend='django.contrib.auth.backends.ModelBackend')
        request.session['demo_username'] = username
        role_name = user.get_full_name() or user.username
        messages.success(request, f"Đã chuyển sang tài khoản: {role_name} ({username})")
    else:
        messages.error(request, f"Không tìm thấy tài khoản {username}")
    
    referer = request.META.get('HTTP_REFERER')
    if referer and 'switch-user' not in referer:
        return redirect(referer)
    
    # Điều hướng thông minh theo vai trò
    if hasattr(user, 'profile') and user.profile.role == 'RESCUER':
        return redirect('rescuer_dashboard')
    return redirect('rescue_create')


# ==========================================
# 1. QUẢN LÝ TÀI KHOẢN (ĐĂNG NHẬP & ĐĂNG KÝ)
# ==========================================
def login_view(request):
    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        user = User.objects.filter(username=username).first()
        if user:
            auth.login(request, user, backend='django.contrib.auth.backends.ModelBackend')
            request.session['demo_username'] = username
            messages.success(request, f"Đăng nhập thành công! Xin chào {user.get_full_name() or user.username}.")
            if hasattr(user, 'profile') and user.profile.role == 'RESCUER':
                return redirect("rescuer_dashboard")
            return redirect("rescue_create")
        else:
            messages.error(request, f"Tài khoản '{username}' không tồn tại. Vui lòng chọn trong danh sách có sẵn.")
    
    demo_users = User.objects.select_related('profile').all()
    return render(request, "accounts/login.html", {"demo_users": demo_users})


def logout_view(request):
    auth.logout(request)
    messages.info(request, "Đã đăng xuất khỏi hệ thống.")
    return redirect("login")


def register_view(request):
    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        full_name = request.POST.get("full_name", "").strip()
        phone = request.POST.get("phone", "").strip()
        role = request.POST.get("role", "VICTIM")
        vehicle_type = request.POST.get("vehicle_type", "Xe máy")

        if User.objects.filter(username=username).exists():
            messages.error(request, "Tên tài khoản này đã được sử dụng!")
            return render(request, "accounts/register.html")

        user = User.objects.create_user(
            username=username,
            password="password123",
            first_name=full_name,
            is_active=True
        )
        UserProfile.objects.create(
            user=user,
            role=role,
            phone=phone,
            vehicle_type=vehicle_type,
            rescuer_status='READY' if role in ['RESCUER', 'BOTH'] else 'OFFLINE',
            current_latitude=16.0748 + random.uniform(-0.02, 0.02),
            current_longitude=108.1499 + random.uniform(-0.02, 0.02)
        )
        auth.login(request, user, backend='django.contrib.auth.backends.ModelBackend')
        messages.success(request, f"Chào mừng {full_name}! Tài khoản của bạn đã được khởi tạo thành công.")
        
        if role in ['RESCUER', 'BOTH']:
            return redirect("rescuer_dashboard")
        return redirect("rescue_create")

    return render(request, "accounts/register.html")


# ==========================================
# 2. TẠO YÊU CẦU CỨU HỘ KHẨN CẤP (SOS)
# ==========================================
def create_request_view(request):
    current_user = get_current_user(request)
    profile = getattr(current_user, 'profile', None)

    # Thợ cứu hộ không dùng trang tạo SOS -> Tự động chuyển về Bảng nhận ca của thợ
    if profile and profile.role == 'RESCUER':
        return redirect("rescuer_dashboard")
    
    if request.method == "POST":
        location_address = request.POST.get("location_address", "120 Hoàng Minh Thảo, Liên Chiểu, Đà Nẵng")
        latitude = request.POST.get("latitude")
        longitude = request.POST.get("longitude")
        vehicle_type = request.POST.get("vehicle_type", "Xe máy")
        issue_type = request.POST.get("issue_type", "Thủng săm / Xẹp lốp")
        other_vehicle_text = request.POST.get("other_vehicle_text", "").strip()
        other_issue_text = request.POST.get("other_issue_text", "").strip()

        issue_mapping = {
            'puncture': 'Thủng săm / Xẹp lốp',
            'battery': 'Hỏng bình ắc quy / Kích bình',
            'fuel': 'Hết xăng giữa đường',
            'engine': 'Chết máy / Ngập nước',
            'chain_brake': 'Đứt xích / Bó kẹt phanh',
            'key': 'Mất chìa khóa / Kẹt Smartkey',
            'accident': 'Va chạm giao thông',
            'other_issue': other_issue_text or 'Sự cố khác',
        }
        vehicle_mapping = {
            'motorcycle': 'Xe máy',
            'car': 'Xe ô tô (4 - 7 chỗ)',
            'electric_bike': 'Xe máy điện / Xe đạp điện',
            'bicycle': 'Xe đạp',
            'other_vehicle': other_vehicle_text or 'Phương tiện khác',
        }
        issue_type = issue_mapping.get(issue_type, issue_type)
        vehicle_type = vehicle_mapping.get(vehicle_type, vehicle_type)

        description = request.POST.get("description", "")
        proposed_fee = request.POST.get("proposed_fee", "")

        try:
            latitude = float(latitude) if latitude else 16.0725
            longitude = float(longitude) if longitude else 108.1520
        except ValueError:
            latitude = 16.0725
            longitude = 108.1520

        # Sinh mã cứu hộ độc nhất
        code = f"SX-{random.randint(1000, 9999)}"

        # Nếu đang ở tài khoản Thợ mà bấm gửi SOS, tự động gán cho tài khoản Nạn nhân để dữ liệu chuẩn vai trò
        actual_victim = current_user
        if hasattr(current_user, 'profile') and current_user.profile.role == 'RESCUER':
            demo_victim = User.objects.filter(username='nan_nhan').first()
            if demo_victim:
                actual_victim = demo_victim

        # Tự động hủy các ca cũ đang PENDING chưa có thợ nhận của nạn nhân này để tránh trùng lặp
        RescueRequest.objects.filter(victim=actual_victim, status='PENDING').update(status='CANCELLED')

        # Xử lý lưu các ảnh hiện trường sự cố do người dùng tải lên (hỗ trợ nhiều ảnh)
        image_urls = []
        uploaded_images = request.FILES.getlist('incident_images')
        if uploaded_images:
            import time
            from django.core.files.storage import default_storage
            from django.core.files.base import ContentFile
            for idx, img_file in enumerate(uploaded_images[:3]):
                ext = os.path.splitext(img_file.name)[1].lower() or '.jpg'
                file_name = f"incidents/{code}_{idx}_{int(time.time())}{ext}"
                saved_path = default_storage.save(file_name, ContentFile(img_file.read()))
                image_urls.append(f"/media/{saved_path}")

        image_url = ",".join(image_urls)

        # Pre-condition: Lưu yêu cầu với thông tin vị trí, xe, sự cố
        rescue_req = RescueRequest.objects.create(
            code=code,
            victim=actual_victim,
            vehicle_type=vehicle_type,
            issue_type=issue_type,
            description=description,
            image_url=image_url,
            location_address=location_address,
            latitude=latitude,
            longitude=longitude,
            proposed_fee=proposed_fee,
            status='PENDING'
        )

        # Main flow 2: Quét tìm người hỗ trợ phù hợp trong bán kính 10 km
        # Pre-conditions & Business rules:
        # - Tài khoản đang hoạt động (user.is_active = True)
        # - Trạng thái: 'READY' (Sẵn sàng hỗ trợ)
        # - Khoảng cách <= 10.0 km
        rescuers = UserProfile.objects.select_related('user').filter(
            user__is_active=True,
            role__in=['RESCUER', 'BOTH'],
            rescuer_status='READY'
        ).exclude(user=current_user)

        found_helpers = []
        for helper_profile in rescuers:
            dist = calculate_distance_km(
                latitude, longitude,
                helper_profile.current_latitude, helper_profile.current_longitude
            )
            if dist <= 10.0:
                found_helpers.append((helper_profile, dist))
                
                # Main flow 3: Gửi thông báo đến người hỗ trợ phù hợp
                Notification.objects.create(
                    user=helper_profile.user,
                    rescue_request=rescue_req,
                    title="SOS Cứu hộ mới trong khu vực!",
                    content=f"Yêu cầu #{rescue_req.code}: {rescue_req.issue_type} ({rescue_req.vehicle_type}) cách bạn ~{dist} km tại {location_address}",
                    notification_type='NEW_REQUEST'
                )
                
                # Business rule 9: Ghi nhận lịch sử gửi thông báo
                RescueResponseLog.objects.create(
                    request=rescue_req,
                    rescuer=helper_profile.user,
                    action='NOTIFIED',
                    note=f"Đã phát thông báo đến thợ trong bán kính 10km (Cách {dist} km)"
                )

        request.session['current_rescue_id'] = rescue_req.id

        if found_helpers:
            messages.success(
                request, 
                f"Đã phát tín hiệu cứu hộ #{rescue_req.code} thành công! Tìm thấy {len(found_helpers)} người hỗ trợ sẵn sàng trong bán kính 10km."
            )
        else:
            # Exception flow 2a: Không tìm thấy người hỗ trợ trong bán kính 10 km
            messages.warning(
                request, 
                f"Tín hiệu #{rescue_req.code} đã phát! Hiện chưa có người hỗ trợ nào trong bán kính 10km. Hệ thống đang giữ yêu cầu và tiếp tục quét mở rộng..."
            )

        return redirect("victim_dashboard")

    # Lấy các yêu cầu gần nhất của người dùng hiện tại
    my_requests = RescueRequest.objects.filter(victim=current_user).order_by('-created_at')[:5]
    
    context = {
        "current_user": current_user,
        "my_requests": my_requests,
    }
    return render(request, "rescue/create_request.html", context)


# ==========================================
# 3. TRANG DASHBOARD TIẾP NHẬN DÀNH CHO NGƯỜI CỨU HỘ
# ==========================================
# 3. TRANG DASHBOARD TIẾP NHẬN & THEO DÕI CA CỨU HỘ
#    (PHÂN BIỆT GIAO DIỆN DÀNH CHO THỢ VÀ NẠN NHÂN)
# ==========================================
def rescuer_dashboard_view(request, view_as=None):
    """
    Main flow 4 & 5 & Victim Rescue Tracking Flow:
    - Nếu là Người cứu hộ / Thợ (RESCUER):
      Hiển thị bảng nhận ca, radar quét các yêu cầu trong bán kính 10km,
      công tắc Sẵn sàng nhận ca, các ca thợ đang xử lý.
    - Nếu là Người gặp nạn (VICTIM):
      Hiển thị tiến trình ca cứu hộ của nạn nhân (ca đang phát chờ thợ nhận,
      danh sách thợ lân cận đang nhận chuông, thông tin thợ đã nhận ca và đang tới,
      lịch sử các ca đã gửi, nút hủy ca).
    Hỗ trợ tham số ?view_as=victim hoặc ?view_as=rescuer để người dùng / giám khảo
    dễ dàng đối chiếu giao diện 2 bên mà không cần đổi tài khoản.
    """
    current_user = get_current_user(request)
    profile = getattr(current_user, 'profile', None)

    if not profile:
        profile = UserProfile.objects.create(user=current_user, role='RESCUER', rescuer_status='READY')

    # Xác định góc nhìn:
    # Nếu user là Thợ (RESCUER), LUÔN LUÔN hiển thị Bảng nhận ca (rescuer_dashboard)
    if profile.role == 'RESCUER':
        req_view = 'rescuer'
    else:
        req_view = request.GET.get('view_as') or view_as or 'victim'

    # ----------------------------------------------------
    # GÓC NHÌN 1: DÀNH CHO NGƯỜI GẶP NẠN (VICTIM DASHBOARD)
    # ----------------------------------------------------
    if req_view == 'victim':
        # 1. Tìm ca cứu hộ đang hoạt động của chính nạn nhân này (PENDING, ACCEPTED, IN_PROGRESS, ARRIVED)
        active_request = RescueRequest.objects.filter(
            victim=current_user,
            status__in=['PENDING', 'ACCEPTED', 'IN_PROGRESS', 'ARRIVED']
        ).order_by('-created_at').first()

        nearby_rescuers = []
        helper_profile = None
        distance_km = 1.2
        eta_minutes = 3

        if active_request:
            if active_request.status == 'PENDING':
                # Tìm các thợ sẵn sàng trong bán kính 10km đang nhận tín hiệu SOS này
                rescuers_qs = UserProfile.objects.select_related('user').filter(
                    user__is_active=True,
                    role__in=['RESCUER', 'BOTH'],
                    rescuer_status='READY'
                ).exclude(user=current_user)

                for r_prof in rescuers_qs:
                    d = calculate_distance_km(
                        active_request.latitude, active_request.longitude,
                        r_prof.current_latitude, r_prof.current_longitude
                    )
                    if d <= 10.0:
                        r_prof.distance_km = d
                        r_prof.eta_minutes = max(3, round(d / 25 * 60))
                        nearby_rescuers.append(r_prof)
                nearby_rescuers.sort(key=lambda x: x.distance_km)

            elif active_request.helper:
                helper_profile = getattr(active_request.helper, 'profile', None)
                if helper_profile:
                    distance_km = calculate_distance_km(
                        helper_profile.current_latitude, helper_profile.current_longitude,
                        active_request.latitude, active_request.longitude
                    )
                    eta_minutes = max(2, round(distance_km / 25 * 60))
                active_request.distance_km = distance_km
                active_request.eta_minutes = eta_minutes

        # 2. Lịch sử các ca cứu hộ trước đây của nạn nhân
        past_requests = RescueRequest.objects.filter(victim=current_user).order_by('-created_at')
        if active_request:
            past_requests = past_requests.exclude(id=active_request.id)
        past_requests = past_requests[:10]

        # 3. Thống kê ca của nạn nhân
        total_requests = RescueRequest.objects.filter(victim=current_user).count()
        completed_requests = RescueRequest.objects.filter(victim=current_user, status='COMPLETED').count()

        # 4. Lịch sử thông báo gửi tới nạn nhân
        notifications = Notification.objects.filter(user=current_user).order_by('-created_at')[:10]

        context = {
            "current_user": current_user,
            "profile": profile,
            "view_as": "victim",
            "active_request": active_request,
            "nearby_rescuers": nearby_rescuers,
            "helper_profile": helper_profile,
            "distance_km": distance_km,
            "eta_minutes": eta_minutes,
            "past_requests": past_requests,
            "total_requests": total_requests,
            "completed_requests": completed_requests,
            "notifications": notifications,
        }
        return render(request, "rescue/victim_dashboard.html", context)

    # ----------------------------------------------------
    # GÓC NHÌN 2: DÀNH CHO THỢ CỨU HỘ (RESCUER DASHBOARD)
    # ----------------------------------------------------
    # Lấy tất cả yêu cầu đang PENDING
    pending_requests = RescueRequest.objects.filter(status='PENDING').select_related('victim')
    
    # Tính khoảng cách và lọc bán kính 10km
    nearby_requests = []
    for req in pending_requests:
        dist = calculate_distance_km(
            profile.current_latitude, profile.current_longitude,
            req.latitude, req.longitude
        )
        if dist <= 10.0:
            req.distance_km = dist
            req.eta_minutes = max(3, round(dist / 25 * 60))
            nearby_requests.append(req)

    # Sắp xếp theo khoảng cách gần nhất
    nearby_requests.sort(key=lambda x: x.distance_km)

    # Các ca đang tiếp nhận/hỗ trợ của người cứu hộ này
    active_rescues = RescueRequest.objects.filter(
        helper=current_user,
        status__in=['ACCEPTED', 'IN_PROGRESS', 'ARRIVED']
    ).select_related('victim')

    # Lịch sử thông báo của người cứu hộ
    notifications = Notification.objects.filter(user=current_user).order_by('-created_at')[:10]

    context = {
        "current_user": current_user,
        "profile": profile,
        "view_as": "rescuer",
        "nearby_requests": nearby_requests,
        "active_rescues": active_rescues,
        "notifications": notifications,
        "radius_km": 10,
    }
    return render(request, "rescue/rescuer_dashboard.html", context)


# ==========================================
# 4. XEM CHI TIẾT YÊU CẦU CỨU HỘ (MAIN FLOW 5, 6 & ALT 6A)
# ==========================================
def request_detail_view(request, request_id):
    """
    Main flow 5, 6: Hệ thống hiển thị chi tiết yêu cầu gồm vị trí, loại xe, sự cố.
    Alternative flow 6a: Người hỗ trợ xem thêm hồ sơ người gặp sự cố trước khi quyết định.
    """
    current_user = get_current_user(request)
    rescue_req = get_object_or_404(RescueRequest.objects.select_related('victim__profile'), id=request_id)
    profile = getattr(current_user, 'profile', None)

    dist = 1.2
    if profile:
        dist = calculate_distance_km(
            profile.current_latitude, profile.current_longitude,
            rescue_req.latitude, rescue_req.longitude
        )
        # Ghi log đã xem
        RescueResponseLog.objects.get_or_create(
            request=rescue_req,
            rescuer=current_user,
            action='VIEWED',
            defaults={'note': f'Xem chi tiết ca cứu hộ (Khoảng cách {dist} km)'}
        )

    # Thống kê hồ sơ người gặp sự cố (Alt 6a)
    victim_profile = getattr(rescue_req.victim, 'profile', None)
    victim_stats = {
        "total_requests": RescueRequest.objects.filter(victim=rescue_req.victim).count(),
        "completed_requests": RescueRequest.objects.filter(victim=rescue_req.victim, status='COMPLETED').count(),
    }

    context = {
        "rescue_req": rescue_req,
        "distance_km": dist,
        "eta_minutes": max(3, round(dist / 25 * 60)),
        "victim_profile": victim_profile,
        "victim_stats": victim_stats,
        "profile": profile,
    }
    return render(request, "rescue/request_detail.html", context)


# ==========================================
# 5. CHẤP NHẬN HỖ TRỢ (MAIN FLOW 8 - 12 & EXCEPTIONS)
# ==========================================
@require_POST
def accept_request_view(request, request_id):
    """
    Main flow:
    8. Người hỗ trợ quyết định chấp nhận hỗ trợ.
    9. Nếu chấp nhận, hệ thống gán người hỗ trợ cho yêu cầu.
    10. Cập nhật trạng thái yêu cầu thành Đã tiếp nhận.
    11. Cập nhật trạng thái người hỗ trợ thành Đang hỗ trợ.
    12. Hệ thống thông báo cho người gặp sự cố.
    13. Hiển thị giao diện liên lạc và theo dõi trạng thái, bản đồ dẫn đường real-time.

    Exceptions handled:
    - 9a: Yêu cầu đã được người khác tiếp nhận hoặc đã bị hủy.
    - 9b: Người hỗ trợ không còn sẵn sàng (không ở trạng thái READY hoặc bị khóa).
    - 8b: Concurrency control - chỉ người chấp nhận đầu tiên được ghi nhận.
    - 12a: Rollback an toàn nếu có lỗi cơ sở dữ liệu.
    """
    current_user = get_current_user(request)
    profile = getattr(current_user, 'profile', None)

    # Business rule 1 & Exception 9b: Kiểm tra tài khoản đang hoạt động
    if not current_user.is_active:
        messages.error(request, "Tài khoản của bạn đã bị khóa hoặc không hoạt động.")
        return redirect("rescuer_dashboard")

    # Business rule 2: Người hỗ trợ phải ở trạng thái 'Sẵn sàng hỗ trợ'
    if not profile or profile.rescuer_status != 'READY':
        messages.error(request, "Bạn đang không ở trạng thái Sẵn sàng hỗ trợ (Vui lòng bật trạng thái Sẵn sàng để nhận ca).")
        return redirect("rescuer_dashboard")

    try:
        # Concurrency Lock (Atomic Transaction) xử lý Alternative flow 8b
        with transaction.atomic():
            # Khóa bản ghi RescueRequest để tránh 2 người cùng chấp nhận đồng thời
            req = RescueRequest.objects.select_for_update().filter(id=request_id).first()

            if not req:
                messages.error(request, "Không tìm thấy yêu cầu cứu hộ tương ứng.")
                return redirect("rescuer_dashboard")

            # Exception flow 9a & Business rule 7:
            # Yêu cầu đã Đã tiếp nhận, Đang hỗ trợ, Đã hoàn thành, Đã hủy hoặc không còn PENDING
            if req.status != 'PENDING' or req.helper is not None:
                messages.warning(
                    request,
                    f"Rất tiếc! Yêu cầu #{req.code} đã được người hỗ trợ khác tiếp nhận hoặc đã kết thúc."
                )
                return redirect("rescuer_dashboard")

            # Main flow 8: Gán người hỗ trợ cho yêu cầu
            req.helper = current_user
            
            # Main flow 9: Cập nhật trạng thái yêu cầu thành 'Đã tiếp nhận' (ACCEPTED)
            req.status = 'ACCEPTED'
            req.save()

            # Main flow 10: Cập nhật trạng thái người hỗ trợ thành 'Đang hỗ trợ' (BUSY)
            profile.rescuer_status = 'BUSY'
            profile.save()

            # Business rule 9: Ghi nhận lịch sử chấp nhận
            RescueResponseLog.objects.create(
                request=req,
                rescuer=current_user,
                action='ACCEPTED',
                note=f"Người hỗ trợ {current_user.get_full_name() or current_user.username} đã chấp nhận ca #{req.code}"
            )

            # Main flow 11: Hệ thống gửi thông báo cho người gặp sự cố
            Notification.objects.create(
                user=req.victim,
                rescue_request=req,
                title="Đã có người hỗ trợ tiếp nhận!",
                content=(
                    f"Người hỗ trợ {current_user.get_full_name() or current_user.username} "
                    f"({profile.vehicle_plate}) đã chấp nhận yêu cầu #{req.code}. Đang bắt đầu di chuyển đến vị trí của bạn!"
                ),
                notification_type='ACCEPTED'
            )

            # Tạo tin nhắn hệ thống chào đầu tiên
            ChatMessage.objects.create(
                request=req,
                sender=current_user,
                receiver=req.victim,
                message=f"Chào bạn! Tôi đã nhận ca #{req.code}. Tôi đang di chuyển xe ({profile.vehicle_type} - {profile.vehicle_plate}) qua chỗ bạn ngay!"
            )

        messages.success(
            request, 
            f"Bạn đã tiếp nhận thành công ca #{req.code}! Đang mở bản đồ dẫn đường và kênh liên lạc."
        )
        # Main flow 12 & AD Fork: Chuyển đến giao diện theo dõi và dẫn đường real-time
        return redirect(f"/rescue/tracking/?request_id={req.id}")

    except Exception as e:
        # Exception flow 12a: Không thể cập nhật trạng thái
        messages.error(request, f"Không thể xử lý yêu cầu, vui lòng thử lại. ({str(e)})")
        return redirect(f"/rescue/detail/{request_id}/")


# ==========================================
# 6. TỪ CHỐI HỖ TRỢ (ALTERNATIVE FLOW 8A)
# ==========================================
@require_POST
def reject_request_view(request, request_id):
    """
    Alternative flow 8a:
    Người hỗ trợ chọn Từ chối hỗ trợ: hệ thống ghi nhận từ chối và tiếp tục tìm người hỗ trợ khác.
    """
    current_user = get_current_user(request)
    req = get_object_or_404(RescueRequest, id=request_id)
    reason = request.POST.get("reason", "Người hỗ trợ bận hoặc không thể tới vị trí này.")

    # Business rule 9: Ghi nhận lịch sử từ chối
    RescueResponseLog.objects.create(
        request=req,
        rescuer=current_user,
        action='REJECTED',
        note=f"Từ chối ca #{req.code}: {reason}"
    )

    messages.info(
        request, 
        f"Bạn đã từ chối ca #{req.code}. Hệ thống tiếp tục giữ yêu cầu để tìm người hỗ trợ khác phù hợp."
    )
    return redirect("rescuer_dashboard")


# ==========================================
# 6B. HỦY YÊU CẦU CỨU HỘ (DÀNH CHO NẠN NHÂN)
# ==========================================
@require_POST
def cancel_request_view(request, request_id):
    """
    Người gặp nạn chủ động hủy yêu cầu cứu hộ nếu xe đã tự khắc phục
    hoặc không còn nhu cầu cứu hộ.
    """
    current_user = get_current_user(request)
    req = get_object_or_404(RescueRequest, id=request_id)
    profile = getattr(current_user, 'profile', None)

    if req.victim == current_user or (profile and profile.role == 'VICTIM') or current_user.is_staff or current_user.username == 'nan_nhan':
        req.status = 'CANCELLED'
        req.save()
        RescueResponseLog.objects.create(
            request=req,
            rescuer=current_user,
            action='CANCELLED',
            note=f"Người gặp nạn đã chủ động hủy ca #{req.code}"
        )
        if request.session.get('current_rescue_id') == req.id:
            request.session.pop('current_rescue_id', None)
        messages.info(request, f"Đã hủy yêu cầu cứu hộ #{req.code} thành công.")
    else:
        messages.error(request, "Bạn không có quyền hủy yêu cầu này.")
    return redirect("rescuer_dashboard")


# ==========================================
# 7. TRAO ĐỔI & THỐNG NHẤT PHƯƠNG ÁN (MAIN FLOW 7)
#    (TRAO ĐỔI TIN NHẮN RIÊNG TƯ 1 - 1 GIỮA 1 THỢ VÀ 1 NẠN NHÂN)
# ==========================================
def support_chat_view(request):
    """
    Main flow 7: Kênh trao đổi cứu hộ (Lưu trữ và hiển thị tương tự Messenger).
    - Quy tắc 1-1 Messenger: Nếu nhắn tin với cùng 1 người thì chỉ lưu 1 cuộc trò chuyện duy nhất,
      chứa toàn bộ lịch sử tin nhắn giữa 2 người qua các ca cứu hộ.
    - Mặc định: Hiển thị danh sách các cuộc trò chuyện (Inbox gom theo từng người).
      Nếu không có cuộc trò chuyện nào: Chỉ hiển thị tiêu đề 'KÊNH TRAO ĐỔI CỨU HỘ' và 'Không có cuộc trao đổi nào đang diễn ra'.
    - Khi chọn người / ca: Mở phòng chat chi tiết 1-1 với người đó.
    """
    from django.db.models import Q
    from django.utils import timezone

    current_user = get_current_user(request)
    profile = getattr(current_user, 'profile', None)
    is_rescuer = (profile and profile.role == 'RESCUER') or (current_user and current_user.username.startswith('tho'))
    is_victim = not is_rescuer

    req_id = request.GET.get("request_id")
    target_user_id = request.GET.get("user_id")
    rescuer_id_param = request.GET.get("rescuer_id")

    partner_user = None
    rescue_req = None

    if target_user_id:
        partner_user = User.objects.filter(id=target_user_id).first()

    if req_id:
        rescue_req = RescueRequest.objects.filter(id=req_id).first()
        if rescue_req and not partner_user:
            if is_rescuer:
                partner_user = rescue_req.victim
            else:
                partner_user = rescue_req.helper
                if not partner_user and rescuer_id_param:
                    partner_user = User.objects.filter(id=rescuer_id_param).first()
                if not partner_user:
                    # Tìm từ tin nhắn đối phương gửi trong ca này
                    other_m = rescue_req.chat_messages.exclude(sender=current_user).first()
                    if other_m:
                        partner_user = other_m.sender

    # ========================================================
    # CHẾ ĐỘ 1: XEM CHI TIẾT 1 CUỘC TRÒ CHUYỆN (DETAIL CHAT)
    # ========================================================
    if partner_user and partner_user != current_user:
        # Xác định ca cứu hộ liên quan nhất giữa 2 người (ưu tiên ca đang hoạt động)
        active_req = RescueRequest.objects.filter(
            (Q(victim=current_user, helper=partner_user) | Q(victim=partner_user, helper=current_user))
        ).exclude(status__in=['COMPLETED', 'CANCELLED']).order_by('-created_at').first()

        if not rescue_req:
            rescue_req = active_req or RescueRequest.objects.filter(
                (Q(victim=current_user, helper=partner_user) | Q(victim=partner_user, helper=current_user))
            ).order_by('-created_at').first()

        # Nếu vẫn chưa có ca, lấy ca từ tin nhắn cũ nhất/mới nhất giữa 2 người
        if not rescue_req:
            msg_with_req = ChatMessage.objects.filter(
                (Q(sender=current_user, receiver=partner_user) | Q(sender=partner_user, receiver=current_user)),
                request__isnull=False
            ).order_by('-created_at').first()
            if msg_with_req:
                rescue_req = msg_with_req.request

        # Xử lý gửi tin nhắn
        if request.method == "POST":
            message_text = request.POST.get("message_text", "").strip()
            if message_text:
                ChatMessage.objects.create(
                    request=rescue_req or RescueRequest.objects.first(),
                    sender=current_user,
                    receiver=partner_user,
                    message=message_text
                )
                return redirect(f"/rescue/support-chat/?user_id={partner_user.id}")

            action = request.POST.get("action")
            if action == "accept" and is_rescuer and rescue_req:
                return accept_request_view(request, rescue_req.id)
            elif action == "reject" and is_rescuer and rescue_req:
                return reject_request_view(request, rescue_req.id)

        # Lấy TOÀN BỘ lịch sử tin nhắn giữa 2 người (hội thoại hợp nhất 1 cuộc duy nhất)
        chat_messages = ChatMessage.objects.filter(
            (Q(sender=current_user, receiver=partner_user) | Q(sender=partner_user, receiver=current_user)) |
            (Q(sender=current_user, receiver__isnull=True) & (Q(request__victim=partner_user) | Q(request__helper=partner_user))) |
            (Q(sender=partner_user, receiver__isnull=True) & (Q(request__victim=current_user) | Q(request__helper=current_user)))
        ).select_related('sender', 'receiver', 'request').order_by('created_at')

        c_profile = getattr(partner_user, 'profile', None)
        partner_is_rescuer = (c_profile and c_profile.role == 'RESCUER') or (partner_user and partner_user.username.startswith('tho'))

        counterpart_name = partner_user.get_full_name() or partner_user.username
        if partner_is_rescuer:
            counterpart_role = "Thợ cứu hộ"
            counterpart_phone = c_profile.phone if c_profile else "0905123456"
            counterpart_avatar = c_profile.avatar_url if (c_profile and c_profile.avatar_url) else "https://images.unsplash.com/photo-1535713875002-d1d0cf377fde?w=100&auto=format&fit=crop&q=80"
            counterpart_sub = f"{c_profile.vehicle_type} - {c_profile.vehicle_plate}" if c_profile else "Thợ cứu hộ lưu động"
        else:
            counterpart_role = "Người gặp sự cố"
            counterpart_phone = c_profile.phone if c_profile else "0912345678"
            counterpart_avatar = c_profile.avatar_url if (c_profile and c_profile.avatar_url) else "https://images.unsplash.com/photo-1494790108377-be9c29b29330?w=100&auto=format&fit=crop&q=80"
            counterpart_sub = f"Vị trí: {rescue_req.location_address}" if rescue_req else "Người cần hỗ trợ"

        # Tính khoảng cách
        distance_km = 1.2
        if rescue_req and c_profile and hasattr(c_profile, 'current_latitude') and c_profile.current_latitude is not None:
            distance_km = calculate_distance_km(
                float(c_profile.current_latitude), float(c_profile.current_longitude),
                float(rescue_req.latitude), float(rescue_req.longitude)
            )

        context = {
            "view_mode": "detail",
            "current_user": current_user,
            "counterpart_user": partner_user,
            "rescue_req": rescue_req,
            "rescue_id": rescue_req.code if rescue_req else "",
            "rescue_status": rescue_req.get_status_display() if rescue_req else "",
            "location_address": rescue_req.location_address if rescue_req else "",
            "chat_messages": chat_messages,
            "counterpart_name": counterpart_name,
            "counterpart_phone": counterpart_phone,
            "counterpart_role": counterpart_role,
            "counterpart_avatar": counterpart_avatar,
            "counterpart_sub": counterpart_sub,
            "distance_km": distance_km,
            "is_rescuer": is_rescuer,
            "is_victim": is_victim,
        }
        return render(request, "support/chat_and_accept.html", context)

    # ========================================================
    # CHẾ ĐỘ 2: DANH SÁCH CÁC CUỘC TRÒ CHUYỆN (MESSENGER INBOX)
    # LƯU Ý: GOM NHÓM THEO TỪNG NGƯỜI (DUY NHẤT 1 CUỘC TRÒ CHUYỆN/NGƯỜI)
    # ========================================================
    partner_ids = set()

    # 1. Tìm tất cả người đã từng gửi/nhận tin nhắn với current_user
    user_msgs = ChatMessage.objects.filter(
        Q(sender=current_user) | Q(receiver=current_user)
    ).select_related('sender', 'receiver', 'request__victim', 'request__helper')

    for m in user_msgs:
        if m.sender_id and m.sender_id != current_user.id:
            partner_ids.add(m.sender_id)
        if m.receiver_id and m.receiver_id != current_user.id:
            partner_ids.add(m.receiver_id)
        if not m.receiver_id and m.request:
            if m.request.victim_id and m.request.victim_id != current_user.id:
                partner_ids.add(m.request.victim_id)
            if m.request.helper_id and m.request.helper_id != current_user.id:
                partner_ids.add(m.request.helper_id)

    # 2. Tìm thêm từ các ca cứu hộ liên quan trực tiếp
    user_requests = RescueRequest.objects.filter(
        Q(helper=current_user) | Q(victim=current_user)
    ).select_related('victim', 'helper')

    for r in user_requests:
        if r.helper_id == current_user.id and r.victim_id and r.victim_id != current_user.id:
            if r.status not in ['COMPLETED', 'CANCELLED'] or r.chat_messages.exists():
                partner_ids.add(r.victim_id)
        elif r.victim_id == current_user.id and r.helper_id and r.helper_id != current_user.id:
            if r.status not in ['COMPLETED', 'CANCELLED'] or r.chat_messages.exists():
                partner_ids.add(r.helper_id)

    conversations = []
    for pid in partner_ids:
        partner = User.objects.filter(id=pid).first()
        if not partner:
            continue

        p_profile = getattr(partner, 'profile', None)
        partner_is_rescuer = (p_profile and p_profile.role == 'RESCUER') or (partner.username.startswith('tho'))

        # Lấy tin nhắn gần nhất giữa 2 người
        p_messages = ChatMessage.objects.filter(
            (Q(sender=current_user, receiver=partner) | Q(sender=partner, receiver=current_user)) |
            (Q(sender=current_user, receiver__isnull=True) & (Q(request__victim=partner) | Q(request__helper=partner))) |
            (Q(sender=partner, receiver__isnull=True) & (Q(request__victim=current_user) | Q(request__helper=current_user)))
        ).order_by('-created_at')

        last_msg = p_messages.first()

        # Ca liên quan gần nhất
        active_req = RescueRequest.objects.filter(
            (Q(victim=current_user, helper=partner) | Q(victim=partner, helper=current_user))
        ).exclude(status__in=['COMPLETED', 'CANCELLED']).order_by('-created_at').first()

        latest_req = active_req or RescueRequest.objects.filter(
            (Q(victim=current_user, helper=partner) | Q(victim=partner, helper=current_user))
        ).order_by('-created_at').first()

        # Nếu không có tin nhắn nào và không có ca nào đang hoạt động thì bỏ qua
        if not last_msg and not active_req:
            continue

        cp_name = partner.get_full_name() or partner.username
        if partner_is_rescuer:
            cp_avatar = p_profile.avatar_url if (p_profile and p_profile.avatar_url) else "https://images.unsplash.com/photo-1535713875002-d1d0cf377fde?w=100&auto=format&fit=crop&q=80"
            cp_role = "Thợ cứu hộ"
        else:
            cp_avatar = p_profile.avatar_url if (p_profile and p_profile.avatar_url) else "https://images.unsplash.com/photo-1494790108377-be9c29b29330?w=100&auto=format&fit=crop&q=80"
            cp_role = "Người cần cứu"

        conversations.append({
            "partner_id": partner.id,
            "id": latest_req.id if latest_req else None,
            "code": latest_req.code if latest_req else "",
            "counterpart_name": cp_name,
            "counterpart_avatar": cp_avatar,
            "counterpart_role": cp_role,
            "last_message": last_msg.message if last_msg else "Bắt đầu cuộc trao đổi cứu hộ...",
            "last_message_sender": last_msg.sender if last_msg else None,
            "last_time": last_msg.created_at if last_msg else (latest_req.created_at if latest_req else timezone.now()),
            "status": latest_req.status if latest_req else "",
            "status_display": latest_req.get_status_display() if latest_req else "",
            "is_active": bool(active_req),
        })

    # Sắp xếp theo tin nhắn mới nhất
    conversations.sort(key=lambda x: x["last_time"], reverse=True)

    context = {
        "view_mode": "list",
        "current_user": current_user,
        "is_rescuer": is_rescuer,
        "is_victim": is_victim,
        "conversations": conversations,
    }
    return render(request, "support/chat_and_accept.html", context)


# ==========================================
# 8. THEO DÕI VỊ TRÍ THỜI GIAN THỰC & BẢN ĐỒ LỘ TRÌNH (AD FORK 2)
# ==========================================
def live_tracking_view(request):
    """
    Hiển thị giao diện định vị và lộ trình thời gian thực:
    - Nếu có ca cứu hộ ĐANG HOẠT ĐỘNG (ACCEPTED, IN_PROGRESS, ARRIVED):
        Hiển thị lộ trình 2 chiều giữa thợ và người gặp nạn, khoảng cách, ETA và các thao tác ca.
    - Nếu KHÔNG có ca hoặc ca ĐÃ XONG / THỢ ĐÃ NHẤN HOÀN TẤT (COMPLETED, CANCELLED):
        Không hiển thị ca làm đó nữa. Chỉ hiển thị vị trí hiện tại của chính người đang đăng nhập.
    """
    current_user = get_current_user(request)
    profile = getattr(current_user, 'profile', None)

    # 1. Thông tin vị trí người đang đăng nhập
    my_lat = float(profile.current_latitude) if (profile and profile.current_latitude is not None) else 16.0748
    my_lng = float(profile.current_longitude) if (profile and profile.current_longitude is not None) else 108.1499
    my_name = current_user.get_full_name() or (current_user.username if current_user else "Người dùng SafeXe")
    my_role = profile.role if profile else ('RESCUER' if (current_user and current_user.username.startswith('tho')) else 'VICTIM')
    is_rescuer = (my_role == 'RESCUER') or (current_user and current_user.username.startswith('tho'))
    my_avatar = profile.avatar_url if (profile and profile.avatar_url) else "https://images.unsplash.com/photo-1535713875002-d1d0cf377fde?w=100&auto=format&fit=crop&q=80"
    my_phone = profile.phone if (profile and profile.phone) else "0905123456"
    my_vehicle = f"{profile.vehicle_type} - {profile.vehicle_plate}" if (profile and profile.vehicle_type) else "Xe máy cứu hộ"
    rescuer_status = profile.rescuer_status if profile else 'READY'

    # 2. Kiểm tra ca cứu hộ đang hoạt động (chỉ chấp nhận các ca chưa xong: ACCEPTED, IN_PROGRESS, ARRIVED)
    ACTIVE_STATUSES = ['ACCEPTED', 'IN_PROGRESS', 'ARRIVED']
    req_id = request.GET.get("request_id") or request.session.get("current_rescue_id")

    rescue_req = None
    if req_id:
        candidate = RescueRequest.objects.filter(id=req_id).first()
        # Chỉ nhận nếu ca này ĐANG HOẠT ĐỘNG!
        # Nếu candidate.status == 'COMPLETED' hoặc 'CANCELLED' -> Ca đã xong/hoàn tất, không hiển thị ca này nữa!
        if candidate and candidate.status in ACTIVE_STATUSES:
            rescue_req = candidate
        else:
            if request.session.get('current_rescue_id') == req_id:
                request.session.pop('current_rescue_id', None)

    # Nếu không có ca từ req_id hoặc ca đó đã hoàn tất, tìm xem người dùng hiện tại có ca active nào khác không
    if not rescue_req and current_user:
        if is_rescuer:
            rescue_req = RescueRequest.objects.filter(
                helper=current_user,
                status__in=ACTIVE_STATUSES
            ).order_by('-updated_at').first()
        else:
            rescue_req = RescueRequest.objects.filter(
                victim=current_user,
                status__in=ACTIVE_STATUSES
            ).order_by('-updated_at').first()

    has_active_rescue = bool(rescue_req)

    # 3. Chuẩn bị context tùy theo trạng thái
    if has_active_rescue:
        helper_profile = getattr(rescue_req.helper, 'profile', None) if rescue_req.helper else None
        victim_profile = getattr(rescue_req.victim, 'profile', None) if rescue_req.victim else None

        v_lat = float(rescue_req.latitude)
        v_lng = float(rescue_req.longitude)
        h_lat = float(helper_profile.current_latitude) if (helper_profile and helper_profile.current_latitude is not None) else 16.0780
        h_lng = float(helper_profile.current_longitude) if (helper_profile and helper_profile.current_longitude is not None) else 108.1580

        dist = calculate_distance_km(h_lat, h_lng, v_lat, v_lng)
        eta = max(2, round(dist / 25 * 60))
        is_victim = (rescue_req.victim == current_user) or (not is_rescuer)

        context = {
            "current_user": current_user,
            "has_active_rescue": True,
            "rescue_req": rescue_req,
            "rescue_id": rescue_req.code,
            "status": rescue_req.status,
            "eta_minutes": eta,
            "distance_km": dist,
            "is_victim": is_victim,
            "is_rescuer": is_rescuer,
            "helper_name": rescue_req.helper.get_full_name() if (rescue_req.helper and rescue_req.helper.get_full_name()) else (rescue_req.helper.username if rescue_req.helper else "Thợ cứu hộ"),
            "helper_phone": helper_profile.phone if helper_profile else "0905123456",
            "helper_vehicle": f"{helper_profile.vehicle_type} - {helper_profile.vehicle_plate}" if helper_profile else "Wave Alpha đỏ - 43C1 123.45",
            "helper_profile": helper_profile,
            "victim_name": rescue_req.victim.get_full_name() if (rescue_req.victim and rescue_req.victim.get_full_name()) else (rescue_req.victim.username if rescue_req.victim else "Lê Thị Mai"),
            "victim_phone": victim_profile.phone if victim_profile else "0912345678",
            "victim_avatar": victim_profile.avatar_url if victim_profile else "https://images.unsplash.com/photo-1494790108377-be9c29b29330?w=100&auto=format&fit=crop&q=80",
            "victim_vehicle": rescue_req.vehicle_type,
            "location_address": rescue_req.location_address,
            "victim_lat": f"{v_lat:.6f}",
            "victim_lng": f"{v_lng:.6f}",
            "helper_lat": f"{h_lat:.6f}",
            "helper_lng": f"{h_lng:.6f}",
            # Tọa độ và thông tin người đang đăng nhập
            "my_lat": f"{my_lat:.6f}",
            "my_lng": f"{my_lng:.6f}",
            "my_name": my_name,
            "my_role": my_role,
            "my_avatar": my_avatar,
            "my_phone": my_phone,
            "my_vehicle": my_vehicle,
            "rescuer_status": rescuer_status,
        }
    else:
        # Không có ca hoạt động: CHỈ HIỂN THỊ VỊ TRÍ HIỆN TẠI CỦA NGƯỜI ĐANG ĐĂNG NHẬP
        context = {
            "current_user": current_user,
            "has_active_rescue": False,
            "rescue_req": None,
            "rescue_id": None,
            "status": None,
            "eta_minutes": 0,
            "distance_km": 0,
            "is_victim": not is_rescuer,
            "is_rescuer": is_rescuer,
            "my_lat": f"{my_lat:.6f}",
            "my_lng": f"{my_lng:.6f}",
            "my_name": my_name,
            "my_role": my_role,
            "my_avatar": my_avatar,
            "my_phone": my_phone,
            "my_vehicle": my_vehicle,
            "rescuer_status": rescuer_status,
            "location_address": f"Vị trí GPS: {my_lat:.4f}, {my_lng:.4f}",
            "victim_lat": f"{my_lat:.6f}",
            "victim_lng": f"{my_lng:.6f}",
            "helper_lat": f"{my_lat:.6f}",
            "helper_lng": f"{my_lng:.6f}",
        }
    return render(request, "tracking/live_tracking.html", context)


# ==========================================
# 9. CẬP NHẬT TRẠNG THÁI TIẾN ĐỘ CA CỨU HỘ
# ==========================================
@require_POST
def update_request_status_view(request, request_id):
    """
    Cập nhật trạng thái lộ trình:
    ACCEPTED -> IN_PROGRESS (Đang di chuyển tới) -> ARRIVED (Đã tới) -> COMPLETED (Hoàn thành)
    """
    current_user = get_current_user(request)
    req = get_object_or_404(RescueRequest, id=request_id)
    new_status = request.POST.get("status")

    if new_status in dict(RescueRequest.STATUS_CHOICES):
        req.status = new_status
        req.save()

        # Nếu hoàn thành, giải phóng trạng thái thợ về READY
        if new_status == 'COMPLETED':
            if req.helper and hasattr(req.helper, 'profile'):
                req.helper.profile.rescuer_status = 'READY'
                req.helper.profile.total_rescues += 1
                req.helper.profile.save()

            if request.session.get('current_rescue_id') == req.id:
                request.session.pop('current_rescue_id', None)

            # Tự động gửi tin nhắn hoàn tất ca và mời nạn nhân đánh giá thợ trong kênh trao đổi 1-1
            ChatMessage.objects.create(
                request=req,
                sender=req.helper or current_user,
                receiver=req.victim,
                message=f"Ca cứu hộ #{req.code} đã hoàn tất thành công! Cảm ơn bạn đã tin dùng SafeXe. Bạn vui lòng dành chút thời gian đánh giá chất lượng phục vụ của thợ tại: /rescue/rating/?request_id={req.id} nhé!"
            )

            # Gửi thông báo hệ thống cho người gặp nạn
            if req.victim:
                Notification.objects.create(
                    user=req.victim,
                    rescue_request=req,
                    title="Ca cứu hộ đã hoàn tất!",
                    content=f"Ca cứu hộ #{req.code} đã hoàn tất thành công. Mời bạn đánh giá chất lượng phục vụ của thợ cứu hộ!",
                    notification_type='STATUS_UPDATE'
                )

            messages.success(request, f"Ca cứu hộ #{req.code} đã hoàn thành xuất sắc!")
            
            # Nếu người gọi yêu cầu trở về tab định vị
            next_url = request.POST.get('next')
            if next_url == 'live_tracking':
                return redirect("live_tracking")

            # Đánh giá là nạn nhân đánh giá chứ thợ không đánh giá
            profile = getattr(current_user, 'profile', None)
            is_rescuer = (profile and profile.role == 'RESCUER') or (req.helper and current_user == req.helper and current_user != req.victim)
            if is_rescuer:
                # Chuyển về tab định vị, nơi sẽ hiển thị ngay vị trí hiện tại của thợ và không còn ca làm đó nữa
                return redirect("live_tracking")
            else:
                return redirect(f"/rescue/rating/?request_id={req.id}")

        messages.info(request, f"Đã cập nhật trạng thái ca #{req.code}: {req.get_status_display()}")

    return redirect(f"/rescue/tracking/?request_id={req.id}")


# ==========================================
# 9B. API CẬP NHẬT VỊ TRÍ GPS HIỆN TẠI CỦA NGƯỜI ĐANG ĐĂNG NHẬP
# ==========================================
@require_POST
def api_update_my_location(request):
    """
    API nhận tọa độ GPS thực tế từ Geolocation API của trình duyệt và lưu vào hồ sơ người dùng.
    """
    current_user = get_current_user(request)
    if not current_user:
        return JsonResponse({"status": "error", "message": "Chưa xác thực người dùng"}, status=401)

    lat = None
    lng = None
    try:
        import json
        if request.body:
            data = json.loads(request.body.decode('utf-8'))
            lat = data.get('latitude')
            lng = data.get('longitude')
    except Exception:
        pass

    if lat is None:
        lat = request.POST.get('latitude')
        lng = request.POST.get('longitude')

    try:
        lat = float(lat)
        lng = float(lng)
    except (TypeError, ValueError):
        return JsonResponse({"status": "error", "message": "Tọa độ GPS không hợp lệ"}, status=400)

    profile = getattr(current_user, 'profile', None)
    if profile:
        profile.current_latitude = lat
        profile.current_longitude = lng
        profile.save()
        return JsonResponse({
            "status": "success",
            "message": "Đã cập nhật vị trí GPS thành công",
            "latitude": lat,
            "longitude": lng,
            "username": current_user.username
        })
    return JsonResponse({"status": "error", "message": "Không tìm thấy hồ sơ người dùng"}, status=404)


# ==========================================
# 10. BẬT/TẮT TRẠNG THÁI SẴN SÀNG CỦA NGƯỜI CỨU HỘ
# ==========================================
@require_POST
def toggle_rescuer_status_view(request):
    """
    Người cứu hộ chủ động chuyển đổi trạng thái: Sẵn sàng (READY) <-> Tạm nghỉ (OFFLINE)
    """
    current_user = get_current_user(request)
    profile = getattr(current_user, 'profile', None)
    if profile:
        new_status = request.POST.get("rescuer_status")
        if new_status in ['READY', 'OFFLINE', 'BUSY']:
            profile.rescuer_status = new_status
            profile.save()
            messages.success(request, f"Đã cập nhật trạng thái sang: {profile.get_rescuer_status_display()}")
    return redirect("rescuer_dashboard")


# ==========================================
# 11. ĐÁNH GIÁ SAO & GỬI NHẬN XÉT DỊCH VỤ (CHỈ DÀNH CHO NẠN NHÂN)
# ==========================================
def rating_feedback_view(request):
    """
    Đánh giá sao & nhận xét dịch vụ.
    Chỉ dành cho nạn nhân đánh giá người cứu hộ (thợ không đánh giá).
    """
    current_user = get_current_user(request)
    profile = getattr(current_user, 'profile', None)

    # Thợ không đánh giá -> Chuyển về dashboard tiếp nhận ca
    if profile and profile.role == 'RESCUER' and current_user.username != 'nan_nhan':
        messages.warning(request, "Tính năng đánh giá chỉ dành cho nạn nhân đánh giá người cứu hộ.")
        return redirect("rescuer_dashboard")

    req_id = request.GET.get("request_id")
    rescue_req = None
    if req_id:
        rescue_req = RescueRequest.objects.filter(id=req_id).first()
    else:
        # Lấy ca cứu hộ gần nhất của nạn nhân
        rescue_req = RescueRequest.objects.filter(victim=current_user, status='COMPLETED').order_by('-updated_at').first()
        if not rescue_req:
            rescue_req = RescueRequest.objects.filter(victim=current_user).order_by('-created_at').first()

    if request.method == "POST":
        score_val = request.POST.get("rating_score", "5")
        try:
            score = float(score_val)
        except (ValueError, TypeError):
            score = 5.0

        comment = request.POST.get("comment", "")
        rescue_code = request.POST.get("rescue_id", "")
        
        target_req = RescueRequest.objects.filter(code=rescue_code).first() if rescue_code else rescue_req
        if target_req and target_req.helper and hasattr(target_req.helper, 'profile'):
            hp = target_req.helper.profile
            total = hp.total_rescues if hp.total_rescues > 0 else 1
            hp.rating_avg = round((hp.rating_avg * (total - 1) + score) / total, 1)
            hp.save()

        messages.success(request, f"Cảm ơn bạn đã đánh giá {int(score)} sao cho người cứu hộ! Chúc bạn thượng lộ bình an.")
        return redirect("rescue_create")

    helper = rescue_req.helper if rescue_req else None
    helper_profile = getattr(helper, 'profile', None) if helper else None

    context = {
        "rescue_id": rescue_req.code if rescue_req else "SX-8921",
        "helper_name": helper.get_full_name() if (helper and helper.get_full_name()) else (helper.username if helper else "Nguyễn Văn Hùng"),
        "helper_avatar": helper_profile.avatar_url if (helper_profile and helper_profile.avatar_url) else "https://images.unsplash.com/photo-1535713875002-d1d0cf377fde?w=100&auto=format&fit=crop&q=80",
        "helper_rating": helper_profile.rating_avg if helper_profile else 4.9,
        "issue_type": rescue_req.issue_type if rescue_req else "Vá săm xe máy",
    }
    return render(request, "reviews/rating_feedback.html", context)


# ==========================================
# 12. API POLLING TRẠNG THÁI THỜI GIAN THỰC (AJAX)
# ==========================================
def api_request_status(request, request_id):
    """
    API kiểm tra trạng thái ca cứu hộ thời gian thực cho frontend polling
    """
    req = RescueRequest.objects.filter(id=request_id).first()
    if not req:
        return JsonResponse({"error": "Not found"}, status=404)

    helper_name = req.helper.get_full_name() if req.helper else None
    return JsonResponse({
        "id": req.id,
        "code": req.code,
        "status": req.status,
        "status_display": req.get_status_display(),
        "has_helper": bool(req.helper),
        "helper_name": helper_name,
    })
