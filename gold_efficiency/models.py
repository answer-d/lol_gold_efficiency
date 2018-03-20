from django.db import models

# Create your models here.


class PatchVersion(models.Model):
    """パッチバージョン"""
    version_str = models.CharField(max_length=20)

    def __str__(self):
        return self.version_str


class Item(models.Model):
    """アイテム"""
    riot_item_id = models.PositiveIntegerField()
    name = models.CharField(max_length=50)
    base_cost = models.PositiveIntegerField()
    total_cost = models.PositiveIntegerField()
    is_purchasable = models.BooleanField()
    sell_gold = models.PositiveIntegerField()
    image_json = models.TextField()
    from_item_str = models.CharField(max_length=50, null=True)
    into_item_str = models.CharField(max_length=50, null=True)
    depth = models.PositiveIntegerField(null=True)
    patch_version = models.ForeignKey(PatchVersion, on_delete=models.CASCADE)

    def __str__(self):
        return self.name


class StatsMaster(models.Model):
    """ステータスと金銭価値のベース"""
    STATS_BASE = {
        'FlatArmorMod': 0,
        'FlatCritChanceMod': 0,
        'FlatHPPoolMod': 0,
        'FlatHPRegenMod': 0,
        'FlatMPPoolMod': 0,
        'FlatMagicDamageMod':0,
        'FlatMovementSpeedMod': 0,
        'FlatPhysicalDamageMod': 0,
        'FlatSpellBlockMod': 0,
        'PercentAttackSpeedMod': 0,
        'PercentLifeStealMod': 0,
        'PercentMovementSpeedMod': 0,
    }

    name = models.CharField(max_length=30)
    gold_value_per_amount = models.FloatField()
    patch_version = models.ForeignKey(PatchVersion, on_delete=models.CASCADE)

    def __str__(self):
        return self.name


class Stats(models.Model):
    """アイテムに紐づくステータス"""
    item = models.ForeignKey(Item, on_delete=models.CASCADE)
    stats = models.ForeignKey(StatsMaster, on_delete=models.CASCADE)
    amount = models.FloatField()

    def __str__(self):
        return self.item.name + '_' + self.stats.name


class Effect(models.Model):
    """アイテムに紐づく効果(passive/active)"""
    item = models.ForeignKey(Item, on_delete=models.CASCADE)
    description = models.CharField(max_length=200)
    is_evaluable = models.BooleanField()

    def __str__(self):
        return self.item.name + '_' + self.description


class TagMaster(models.Model):
    """タグのベース"""
    name = models.CharField(max_length=30)
    patch_version = models.ForeignKey(PatchVersion, on_delete=models.CASCADE)

    def __str__(self):
        return self.name


class Tag(models.Model):
    """アイテムに紐づくタグ"""
    # TAGS = {
    #     'GoldPer', 'Damage', 'Health', 'Stealth', 'Consumable', 'Mana', 'Slow',
    #     'NonbootsMovement', 'MagicPenetration', 'Armor', 'Tenacity', 'Boots',
    #     'ArmorPenetration', 'Trinket', 'Aura', 'SpellDamage', 'Vision', 'Jungle',
    #     'LifeSteal', 'Active', 'HealthRegen', 'AttackSpeed', 'Bilgewater', 'OnHit',
    #     'SpellVamp', 'SpellBlock', 'CooldownReduction', 'Lane', 'CriticalStrike',
    #     'ManaRegen'
    # }

    item = models.ForeignKey(Item, on_delete=models.CASCADE)
    tag = models.ForeignKey(TagMaster, on_delete=models.CASCADE)

    def __str__(self):
        return self.item.name + ':' + self.tag.name
