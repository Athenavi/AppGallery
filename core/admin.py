from django.contrib import admin
from .models import Application, AppVersion

class AppVersionInline(admin.TabularInline):
    model = AppVersion
    extra = 1  # 定义额外的空行以供添加新的版本

class ApplicationAdmin(admin.ModelAdmin):
    list_display = ('app_id', 'name', 'description', 'created_at', 'owner')  # 在列表视图中显示的字段
    search_fields = ('name', 'description', 'app_id')  # 可以搜索的字段
    list_filter = ('created_at', 'owner')  # 可以过滤的字段
    inlines = [AppVersionInline]  # 关联AppVersion模型，这样可以在同一页面中管理应用及其版本

class AppVersionAdmin(admin.ModelAdmin):
    list_display = ('application', 'version', 'file_name', 'file_size', 'md5_hash', 'upload_time', 'release_notes')
    search_fields = ('file_name', 'version')
    list_filter = ('application', 'upload_time')

# 注册模型到admin管理界面
admin.site.register(Application, ApplicationAdmin)
admin.site.register(AppVersion, AppVersionAdmin)
