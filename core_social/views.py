from rest_framework import mixins
from rest_framework.generics import get_object_or_404, RetrieveUpdateDestroyAPIView
from rest_framework.permissions import IsAuthenticated

from rest_framework.viewsets import GenericViewSet
from rest_framework_simplejwt.authentication import JWTAuthentication

from core_social.models import Profile
from core_social.serializers import ProfileSerializer, ProfileListSerializer


class CurrentUserProfileView(RetrieveUpdateDestroyAPIView):
    serializer_class = ProfileSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get_object(self):
        """Get user profile"""
        user_profile = get_object_or_404(Profile, user=self.request.user)
        return user_profile

    def destroy(self, request, *args, **kwargs):
        """Delete user and profile"""
        profile = self.get_object()
        user = profile.user
        response = super().destroy(request, *args, **kwargs)
        user.delete()
        return response


class ProfileViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, GenericViewSet):
    queryset = Profile.objects.all()
    serializer_class = ProfileListSerializer
