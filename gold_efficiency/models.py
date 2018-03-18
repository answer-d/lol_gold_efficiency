from django.db import models

# Create your models here.


class Item(models.Model):
    """アイテムのモデル"""
    id = models.PositiveIntegerField(primary_key=True)
    name = models.CharField()
    description = models.TextField()
    gold_json = models.CharField()
    stats_json = models.CharField()
    from_item_id = models.CommaSeparatedIntegerField()
    to_item_id = models.CommaSeparatedIntegerField()
    image_json = models.CharField()
    maps_json = models.CharField()
    tags_json = models.CharField()
    # gold_base = models.PositiveIntegerField()
    # gold_purchasable = models.BooleanField()
    # gold_sell = models.PositiveIntegerField()
    # gold_total = models.PositiveIntegerField()
    # flat_armor_mod = models.DecimalField(max_digits=8, decimal_places=5)
    # flat_crit_chance_mod = models.DecimalField(max_digits=8, decimal_places=5)
    # flat_hp_pool_mod = models.DecimalField(max_digits=8, decimal_places=5)

    def __str__(self):
        return self.name


# class ItemRelation(models.Model):
#     """アイテムの関連付けモデル"""
#     from_item = models.ForeignKey(Item)
#     to_item = models.ForeignKey(Item)
