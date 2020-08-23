from django.contrib import admin
from .models import DataProcessingNode, FileGroup, FileExtension

# Register your models here.
admin.site.register(DataProcessingNode)
admin.site.register(FileGroup)
admin.site.register(FileExtension)
