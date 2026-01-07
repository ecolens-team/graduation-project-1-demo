from django.contrib import admin
from .models import Observation

@admin.register(Observation)
class ObservationAdmin(admin.ModelAdmin):
    list_display = ('species_name', 'confidence', 'user', 'created_at')
    list_filter = ('species_name', 'created_at')