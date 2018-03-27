from django.db import models

# Create your models here.


class PatchVersion(models.Model):
    """パッチバージョン"""
    version_str = models.CharField(max_length=20)

    def __str__(self):
        return self.version_str


class Tag(models.Model):
    """アイテムに紐づくタグ"""
    name = models.CharField(max_length=30)
    verbose_name = models.CharField(max_length=30, null=True, blank=True)

    def __str__(self):
        return self.name


class Item(models.Model):
    """アイテム"""
    name = models.CharField(max_length=50)
    riot_item_id = models.PositiveIntegerField()
    base_cost = models.PositiveIntegerField()
    total_cost = models.PositiveIntegerField()
    is_purchasable = models.BooleanField()
    sell_gold = models.PositiveIntegerField()
    img = models.TextField()
    from_item_str = models.CharField(max_length=200, null=True, blank=True)
    into_item_str = models.CharField(max_length=200, null=True, blank=True)
    depth = models.PositiveIntegerField(null=True, blank=True)
    patch_version = models.ForeignKey(
        PatchVersion, on_delete=models.SET_NULL, null=True)
    tags = models.ManyToManyField(Tag)

    def __str__(self):
        return self.name


class StatsBase(models.Model):
    """ステータスの種類と金銭価値"""
    name = models.CharField(max_length=30)
    gold_efficiency_per_amount = models.FloatField()
    patch_version = models.ForeignKey(PatchVersion, on_delete=models.CASCADE)

    def __str__(self):
        return self.name


class Stats(models.Model):
    """アイテムに紐づくステータス"""
    stats = models.ForeignKey(StatsBase, on_delete=models.CASCADE)
    amount = models.FloatField()
    item = models.ForeignKey(Item, on_delete=models.CASCADE)

    def __str__(self):
        return self.stats.name


class Effect(models.Model):
    """アイテムに紐づく効果(passive/active)"""
    description = models.CharField(max_length=200)
    is_unique = models.BooleanField()
    is_evaluable = models.BooleanField()
    item = models.ForeignKey(Item, on_delete=models.CASCADE)

    def __str__(self):
        return self.description
