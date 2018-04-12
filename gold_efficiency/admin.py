from django.contrib import admin
from .models import PatchVersion, Item, StatsBase, Effect, Tag

# Register your models here.


class EffectInline(admin.StackedInline):
    model = Effect
    extra = 1


class ItemAdmin(admin.ModelAdmin):
    list_display = (
        'name', 'riot_item_id', 'total_cost', 'is_purchasable',
        'from_item_str', 'into_item_str',
        'depth', 'patch_version', '_tags'
    )
    inlines = [
       EffectInline
    ]

    def _tags(self, row):
        return ', '.join([x.name for x in row.tags.all()])


admin.site.register(Item, ItemAdmin)
admin.site.register(PatchVersion)
admin.site.register(StatsBase)
admin.site.register(Effect)
admin.site.register(Tag)
