import math
import uuid
from django.db import models
from django.contrib.auth.models import User


def calculate_distance_km(lat1, lon1, lat2, lon2):
    """
    Tính khoảng cách giữa 2 tọa độ GPS (km) theo công thức Haversine.
    """
    try:
        lat1, lon1, lat2, lon2 = float(lat1), float(lon1), float(lat2), float(lon2)
        R = 6371.0  # Bán kính trái đất tính bằng km
        dlat = math.radians(lat2 - lat1)
        dlon = math.radians(lon2 - lon1)
        a = (
            math.sin(dlat / 2) ** 2
            + math.cos(math.radians(lat1))
            * math.cos(math.radians(lat2))
            * math.sin(dlon / 2) ** 2
        )
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        return round(R * c, 2)
    except Exception:
        return 999.0


class UserProfile(models.Model):
    """
    Hồ sơ mở rộng cho Người dùng (Người gặp nạn / Người cứu hộ)
    """
    ROLE_CHOICES = [
        ('VICTIM', 'Người gặp nạn'),
        ('RESCUER', 'Người cứu hộ / Thợ'),
        ('BOTH', 'Cả hai vai trò'),
    ]

    RESCUER_STATUS_CHOICES = [
        ('READY', 'Sẵn sàng hỗ trợ'),
        ('BUSY', 'Đang hỗ trợ'),
        ('OFFLINE', 'Tạm nghỉ / Ngoại tuyến'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='BOTH')
    phone = models.CharField(max_length=20, default='0905123456')
    avatar_url = models.CharField(
        max_length=255, 
        default='https://images.unsplash.com/photo-1535713875002-d1d0cf377fde?w=100&auto=format&fit=crop&q=80'
    )
    rescuer_status = models.CharField(max_length=20, choices=RESCUER_STATUS_CHOICES, default='READY')
    vehicle_type = models.CharField(max_length=50, default='Honda Wave Alpha')
    vehicle_plate = models.CharField(max_length=20, default='43-C1 123.45')
    
    # Tọa độ vị trí hiện tại của Người hỗ trợ (Mặc định: Khu vực Hòa Khánh, Đà Nẵng)
    current_latitude = models.FloatField(default=16.0748)
    current_longitude = models.FloatField(default=108.1499)
    
    rating_avg = models.FloatField(default=4.9)
    total_rescues = models.IntegerField(default=12)
    bio = models.TextField(blank=True, default='Thợ sửa xe máy lưu động 24/7, vá săm, thay ruột, kích bình ắc quy.')

    def __str__(self):
        return f"{self.user.get_full_name() or self.user.username} ({self.get_role_display()})"

    @property
    def is_available(self):
        """Pre-condition: Tài khoản đang hoạt động và ở trạng thái Sẵn sàng hỗ trợ"""
        return self.user.is_active and self.rescuer_status == 'READY'


class RescueRequest(models.Model):
    """
    Yêu cầu cứu hộ khẩn cấp được gửi từ Người gặp sự cố.
    """
    STATUS_CHOICES = [
        ('PENDING', 'Đang tìm người hỗ trợ'),
        ('ACCEPTED', 'Đã tiếp nhận'),
        ('IN_PROGRESS', 'Đang di chuyển tới'),
        ('ARRIVED', 'Đã tới nơi'),
        ('COMPLETED', 'Đã hoàn thành'),
        ('CANCELLED', 'Đã hủy'),
    ]

    code = models.CharField(max_length=20, unique=True)
    victim = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_requests')
    helper = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='accepted_rescues')
    
    # Pre-condition: Có thông tin vị trí, loại xe và loại sự cố
    vehicle_type = models.CharField(max_length=50, default='Xe máy số')
    issue_type = models.CharField(max_length=100, default='Thủng săm / xẹp lốp')
    description = models.TextField(blank=True)
    image_url = models.CharField(max_length=500, blank=True)
    
    location_address = models.CharField(max_length=255, default='120 Hoàng Minh Thảo, Liên Chiểu, Đà Nẵng')
    latitude = models.FloatField(default=16.0725)
    longitude = models.FloatField(default=108.1520)
    
    proposed_fee = models.CharField(max_length=50, default='', blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"[{self.code}] {self.issue_type} - {self.victim.get_full_name() or self.victim.username}"

    @property
    def image_list(self):
        if not self.image_url:
            return []
        return [url.strip() for url in self.image_url.split(',') if url.strip()]

    def can_be_accepted(self):
        """Business rule 7: Yêu cầu chỉ có thể tiếp nhận khi đang ở trạng thái PENDING"""
        return self.status == 'PENDING' and self.helper is None

    @property
    def issue_display(self):
        mapping = {
            'puncture': 'Thủng săm / Xẹp lốp',
            'battery': 'Hỏng bình ắc quy / Kích bình',
            'fuel': 'Hết xăng giữa đường',
            'engine': 'Chết máy / Ngập nước',
            'chain_brake': 'Đứt xích / Bó kẹt phanh',
            'key': 'Mất chìa khóa / Kẹt Smartkey',
            'accident': 'Va chạm giao thông',
            'other_issue': 'Sự cố khác',
        }
        return mapping.get(self.issue_type, self.issue_type)

    @property
    def vehicle_display(self):
        mapping = {
            'motorcycle': 'Xe máy',
            'car': 'Xe ô tô (4 - 7 chỗ)',
            'electric_bike': 'Xe máy điện / Xe đạp điện',
            'bicycle': 'Xe đạp',
            'other_vehicle': 'Phương tiện khác',
        }
        return mapping.get(self.vehicle_type, self.vehicle_type)



class RescueResponseLog(models.Model):
    """
    Business rule 9: Hệ thống phải ghi nhận lịch sử tiếp nhận hoặc từ chối yêu cầu.
    """
    ACTION_CHOICES = [
        ('NOTIFIED', 'Gửi thông báo'),
        ('VIEWED', 'Đã xem chi tiết'),
        ('ACCEPTED', 'Chấp nhận hỗ trợ'),
        ('REJECTED', 'Từ chối hỗ trợ'),
    ]

    request = models.ForeignKey(RescueRequest, on_delete=models.CASCADE, related_name='response_logs')
    rescuer = models.ForeignKey(User, on_delete=models.CASCADE, related_name='rescue_logs')
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    note = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.rescuer.username} - {self.get_action_display()} - {self.request.code}"


class ChatMessage(models.Model):
    """
    Main flow 7: Người hỗ trợ và người gặp sự cố trao đổi qua tin nhắn và thống nhất phương án.
    Tin nhắn là riêng tư 1-1 giữa 1 tài khoản thợ và 1 tài khoản nạn nhân.
    """
    request = models.ForeignKey(RescueRequest, on_delete=models.CASCADE, related_name='chat_messages')
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_chat_messages')
    receiver = models.ForeignKey(User, null=True, blank=True, on_delete=models.CASCADE, related_name='received_chat_messages')
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"{self.sender.username} -> {self.receiver.username if self.receiver else 'Direct'}: {self.message[:30]}"


class Notification(models.Model):
    """
    Main flow 3 & 11: Thông báo gửi cho Người hỗ trợ và Người gặp nạn.
    """
    TYPE_CHOICES = [
        ('NEW_REQUEST', 'Yêu cầu cứu hộ mới'),
        ('ACCEPTED', 'Yêu cầu đã được tiếp nhận'),
        ('REJECTED', 'Người hỗ trợ từ chối'),
        ('STATUS_UPDATE', 'Cập nhật trạng thái'),
        ('CHAT', 'Tin nhắn mới'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    rescue_request = models.ForeignKey(RescueRequest, on_delete=models.CASCADE, null=True, blank=True)
    title = models.CharField(max_length=200)
    content = models.TextField()
    notification_type = models.CharField(max_length=30, choices=TYPE_CHOICES, default='NEW_REQUEST')
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Thông báo cho {self.user.username}: {self.title}"
