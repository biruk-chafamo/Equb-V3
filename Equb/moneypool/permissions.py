from rest_framework import permissions


class AuthenticatedAndObjectPermissionMixin(object):
    def get_permissions(self):
        if self.request.method in ['GET', 'POST']:
            return [permissions.IsAuthenticated()]
        else:
            return [permissions.DjangoObjectPermissions()]