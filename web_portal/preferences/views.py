from rest_framework import generics
from .models import UserSetting
from .serializers import UserSettingSerializer
from rest_framework.permissions import IsAuthenticated

class UserSettingListCreateView(generics.ListCreateAPIView):
    serializer_class = UserSettingSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return UserSetting.objects.filter(models.Q(user=self.request.user) | models.Q(user__isnull=True))

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
