from rest_framework.throttling import UserRateThrottle


class RoleBasedUserRateThrottle(UserRateThrottle):
    role_scope_map = {
        'admin': 'admin',
        'vendor': 'vendor',
        'customer': 'user',
    }
    default_scope = 'user'

    def allow_request(self, request, view):
        if request.user and request.user.is_authenticated:
            self.scope = self.role_scope_map.get(request.user.role, self.default_scope)
        return super().allow_request(request, view)
