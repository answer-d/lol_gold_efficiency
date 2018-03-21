from django.contrib import admin
from .models import PatchVersion, Item, Stats, Effect, Tag

# Register your models here.


class StatsInline(admin.TabularInline):
    model = Stats
    extra = 1


class EffectInline(admin.StackedInline):
    model = Effect
    extra = 1


class TagInline(admin.TabularInline):
    model = Tag
    extra = 1


class ItemAdmin(admin.ModelAdmin):
    list_display = (
        'name', 'riot_item_id', 'total_cost', 'is_purchasable',
        'from_item_str', 'into_item_str',
        'depth', 'patch_version',
    )
    inlines = [
        StatsInline, EffectInline, TagInline
    ]


admin.site.register(Item, ItemAdmin)
admin.site.register(PatchVersion)
admin.site.register(Stats)
admin.site.register(Effect)
admin.site.register(Tag)
