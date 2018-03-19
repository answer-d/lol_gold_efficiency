from django.db import models

# Create your models here.


class Item(models.Model):
    """アイテムのモデル"""
    riot_item_id = models.PositiveIntegerField()
    name = models.CharField()
    base_cost = models.PositiveIntegerField()
    total_cost = models.PositiveIntegerField()
    is_purchasable = models.BooleanField()
    sell_gold = models.PositiveIntegerField()
    image_json = models.CharField()
    maps_json = models.CharField()
    patch_version = models.CharField()

    def __str__(self):
        return self.name


class Stats(models.Model):
    """アイテムに紐づくステータスのモデル"""
    BASE_VALUE = {
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

    item = models.ForeignKey(Item, on_delete=models.CASCADE)
    name = models.CharField(choices=BASE_VALUE.keys())
    amount = models.FloatField()

    def __str__(self):
        return self.name

    def get_gold_value(self):
        return self.BASE_VALUE[self.name] * self.amount


class Effect(models.Model):
    """アイテムに紐づく効果のモデル"""
    item = models.ForeignKey(Item, on_delete=models.CASCADE)
    description = models.CharField()
    is_evaluable = models.BooleanField()

    def __str__(self):
        return self.description

    def get_gold_value(self):
        if self.is_evaluable:
            return eval(self.gold_value_rule)
        else:
            pass


class Tag(models.Model):
    """アイテムに紐づくタグのモデル"""
    TAGS = {
        'GoldPer', 'Damage', 'Health', 'Stealth', 'Consumable', 'Mana', 'Slow',
        'NonbootsMovement', 'MagicPenetration', 'Armor', 'Tenacity', 'Boots',
        'ArmorPenetration', 'Trinket', 'Aura', 'SpellDamage', 'Vision', 'Jungle',
        'LifeSteal', 'Active', 'HealthRegen', 'AttackSpeed', 'Bilgewater', 'OnHit',
        'SpellVamp', 'SpellBlock', 'CooldownReduction', 'Lane', 'CriticalStrike',
        'ManaRegen'
    }

    item = models.ForeignKey(Item, on_delete=models.CASCADE)
    tag = models.CharField(choices=TAGS, null=True)

    def __str__(self):
        return self.tag
