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
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Get list of profiles and filter by username and name"""
        queryset = super().get_queryset()

        username = self.request.query_params.get("username")
        first_name = self.request.query_params.get("first_name")
        last_name = self.request.query_params.get("last_name")

        if username is not None:
            queryset = queryset.filter(user__username__icontains=username)

        if first_name is not None:
            queryset = queryset.filter(first_name__icontains=first_name)

        if last_name is not None:
            queryset = queryset.filter(last_name__icontains=last_name)

        return queryset
