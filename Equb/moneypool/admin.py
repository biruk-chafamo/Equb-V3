from django.contrib import admin

# Register your models here.
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import *

admin.site.register(User, UserAdmin)
admin.site.register(Equb)
admin.site.register(EqubMembership)
admin.site.register(EqubJoinRequest)
admin.site.register(EqubInviteRequest)
admin.site.register(FriendRequest)
admin.site.register(NewEqubNotification)
admin.site.register(NewMemberNotification)
admin.site.register(NewRoundNotification)

