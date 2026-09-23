from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from safexe.core.models import UserProfile, RescueRequest, Notification, ChatMessage


class Command(BaseCommand):
    help = 'Khởi tạo tài khoản mẫu và dữ liệu ban đầu cho SafeXe'

    def handle(self, *args, **kwargs):
        # 1. Người gặp nạn
        victim_user, _ = User.objects.get_or_create(
            username='nan_nhan',
            defaults={
                'first_name': 'Thị Mai',
                'last_name': 'Lê',
                'email': 'nan_nhan@safexe.vn',
                'is_active': True,
            }
        )
        victim_user.set_password('123456')
        victim_user.save()

        UserProfile.objects.get_or_create(
            user=victim_user,
            defaults={
                'role': 'VICTIM',
                'phone': '0912345678',
                'avatar_url': 'https://images.unsplash.com/photo-1494790108377-be9c29b29330?w=100&auto=format&fit=crop&q=80',
                'current_latitude': 16.0725,
                'current_longitude': 108.1520,
            }
        )

        # 2. Thợ cứu hộ 1: Nguyễn Văn Hùng (Cách ~1.2 km, Sẵn sàng)
        rescuer_1, _ = User.objects.get_or_create(
            username='tho_hung',
            defaults={
                'first_name': 'Văn Hùng',
                'last_name': 'Nguyễn',
                'email': 'hung@safexe.vn',
                'is_active': True,
            }
        )
        rescuer_1.set_password('123456')
        rescuer_1.save()

        profile_1, _ = UserProfile.objects.get_or_create(
            user=rescuer_1,
            defaults={
                'role': 'RESCUER',
                'phone': '0905123456',
                'avatar_url': 'https://images.unsplash.com/photo-1535713875002-d1d0cf377fde?w=100&auto=format&fit=crop&q=80',
                'rescuer_status': 'READY',
                'vehicle_type': 'Wave Alpha đỏ',
                'vehicle_plate': '43C1-123.45',
                'current_latitude': 16.0780,
                'current_longitude': 108.1580,
                'rating_avg': 4.9,
                'total_rescues': 24,
                'bio': 'Chuyên vá săm xe máy, thay lốp không săm, thay ắc quy lưu động khu vực Hòa Khánh, Liên Chiểu.',
            }
        )

        # 3. Thợ cứu hộ 2: Trần Văn Long (Cách ~3.8 km, Sẵn sàng)
        rescuer_2, _ = User.objects.get_or_create(
            username='tho_long',
            defaults={
                'first_name': 'Văn Long',
                'last_name': 'Trần',
                'email': 'long@safexe.vn',
                'is_active': True,
            }
        )
        rescuer_2.set_password('123456')
        rescuer_2.save()

        UserProfile.objects.get_or_create(
            user=rescuer_2,
            defaults={
                'role': 'RESCUER',
                'phone': '0935987654',
                'avatar_url': 'https://images.unsplash.com/photo-1570295999919-56ceb5ecca61?w=100&auto=format&fit=crop&q=80',
                'rescuer_status': 'READY',
                'vehicle_type': 'Exciter 150 đen',
                'vehicle_plate': '43D1-999.88',
                'current_latitude': 16.0650,
                'current_longitude': 108.1700,
                'rating_avg': 4.8,
                'total_rescues': 18,
                'bio': 'Đội cứu hộ xe máy đêm, hỗ trợ xăng, vá lốp, xử lý xe ngập nước.',
            }
        )

        # 4. Thợ cứu hộ 3: Phạm Quốc Bảo (Ngoài bán kính 10km - 15km hoặc bận)
        rescuer_3, _ = User.objects.get_or_create(
            username='tho_bao',
            defaults={
                'first_name': 'Quốc Bảo',
                'last_name': 'Phạm',
                'email': 'bao@safexe.vn',
                'is_active': True,
            }
        )
        rescuer_3.set_password('123456')
        rescuer_3.save()

        UserProfile.objects.get_or_create(
            user=rescuer_3,
            defaults={
                'role': 'RESCUER',
                'phone': '0988776655',
                'avatar_url': 'https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=100&auto=format&fit=crop&q=80',
                'rescuer_status': 'BUSY',
                'vehicle_type': 'Sirius bạc',
                'vehicle_plate': '43K1-666.77',
                'current_latitude': 16.2000,
                'current_longitude': 108.3000,
                'rating_avg': 4.7,
                'total_rescues': 10,
            }
        )

        self.stdout.write(self.style.SUCCESS("Da khoi tao du lieu mau thanh cong!"))
