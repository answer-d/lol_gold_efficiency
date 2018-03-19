from django.db import models

# Create your models here.


class Item(models.Model):
    """アイテムのモデル"""
    # id = models.PositiveIntegerField(primary_key=True)
    riot_item_id = models.PositiveIntegerField()
    name = models.CharField()
    # description = models.TextField()
    # gold_json = models.CharField()
    gold_base = models.PositiveIntegerField()
    gold_purchasable = models.BooleanField()
    gold_sell = models.PositiveIntegerField()
    gold_total = models.PositiveIntegerField()
    # stats_json = models.CharField()
    # flat_armor_mod = models.DecimalField(max_digits=8, decimal_places=5)
    # flat_crit_chance_mod = models.DecimalField(max_digits=8, decimal_places=5)
    # flat_hp_pool_mod = models.DecimalField(max_digits=8, decimal_places=5)
    # from_item_id = models.CommaSeparatedIntegerField()
    # to_item_id = models.CommaSeparatedIntegerField()
    image_json = models.CharField()
    maps_json = models.CharField()
    tags_json = models.CharField()
    version = models.CharField()

    def __str__(self):
        return self.name


class Stats(models.Model):
    """金銭価値のベース(1ADあたり○○Gとかそういう感じ)"""
    name = models.CharField()
    gold_value_base = models.FloatField()


class ItemStats(models.Model):
    """ItemとStatsの紐づけモデル"""
    item = models.ForeignKey(Item, on_delete=models.CASCADE)
    stats = models.ForeignKey(Stats, on_delete=models.CASCADE)
    stats_amount = models.FloatField()


class PassiveGoldValue(models.Model):
    item = models.ForeignKey(Item, on_delete=models.CASCADE)
    description = models.CharField()
    gold_value = models.FloatField()


