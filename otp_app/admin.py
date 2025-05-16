#01-01-25
from django.contrib import admin
from .models import CustomUser, OtpToken, UserProfile, UserActivity, CreditRequest, UploadedFile
from django.contrib.auth.admin import UserAdmin
from .models import Plan, PlanRequest, BillingDetail, Coupon


# Register your models here.
class CustomUserAdmin(UserAdmin):
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'email', 'password1', 'password2')}),
    )


class OtpTokenAdmin(admin.ModelAdmin):
    list_display = ("user", "otp_code")


@admin.register(CreditRequest)
class CreditRequestAdmin(admin.ModelAdmin):
    list_display = ('user', 'requested_credits', 'status', 'timestamp')
    actions = ['approve_requests', 'reject_requests']

    def approve_requests(self, request, queryset):
        queryset.update(status='APPROVED')
        for credit_request in queryset:
            if credit_request.status == 'APPROVED':
                user_profile = UserProfile.objects.get(user=credit_request.user)
                user_profile.credits += credit_request.requested_credits
                user_profile.save()
    approve_requests.short_description = "Approve selected requests"

    def reject_requests(self, request, queryset):
        queryset.update(status='REJECTED')
    reject_requests.short_description = "Reject selected requests"

@admin.register(UploadedFile)
class UploadedFileAdmin(admin.ModelAdmin):
    list_display = ('user', 'file', 'uploaded_at','upload_type')




#16-01-25
@admin.register(Plan)
class PlanAdmin(admin.ModelAdmin):
    list_display = ('name', 'credits', 'price')

@admin.register(PlanRequest)
class PlanRequestAdmin(admin.ModelAdmin):
    list_display = ("user", "plan", "custom_price", "requested_credits", "status", "timestamp")
    list_filter = ('status','user')
    search_fields = ("user__username", "plan__name")
    
    def plan(self, obj):
        return obj.plan.name if obj.plan else 'No Plan Assigned'
    
@admin.register(BillingDetail)
class BillingDetailAdmin(admin.ModelAdmin):
    list_display = ('user','company_name','billing_address','city','state','tax_id')    
    
@admin.register(Coupon)
class CouponAdmin(admin.ModelAdmin):
    list_display = ('code','valid_from','valid_until')
    
admin.site.register(OtpToken, OtpTokenAdmin)
admin.site.register(CustomUser, CustomUserAdmin)
admin.site.register(UserProfile)
admin.site.register(UserActivity)