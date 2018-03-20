from django.contrib import admin
from .models import PatchVersion, Item, StatsMaster, Stats, Effect, TagMaster, Tag

# Register your models here.


admin.site.register(PatchVersion)
admin.site.register(Item)
admin.site.register(StatsMaster)
admin.site.register(Stats)
admin.site.register(Effect)
admin.site.register(TagMaster)
admin.site.register(Tag)
