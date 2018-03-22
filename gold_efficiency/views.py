from django.shortcuts import render
from .models import Item, PatchVersion, Stats, Effect, STAB_TAGS, STAB_STATS_BASE
from decimal import Decimal, ROUND_HALF_UP

# Create your views here.


def dec_round(v, fp):
    """四捨五入マン"""
    return Decimal(v).quantize(Decimal(fp), rounding=ROUND_HALF_UP)


def index(request):
    patch_version = PatchVersion.objects.get(version_str='8.5.2')
    item_records = Item.objects.filter(patch_version=patch_version)

    item_list = list()
    for item in item_records:
        stats_set = Stats.objects.filter(item=item)
        effect_set = Effect.objects.filter(item=item)

        gold_value = 0

        stats_list = list()
        for i in stats_set:
            stats_list.append({
                'name': i.name,
                'amount': i.amount,
                'gold_value': dec_round(STAB_STATS_BASE[i.name] * i.amount, '0.1'),
            })
            gold_value += STAB_STATS_BASE[i.name] * i.amount

        effect_list = list()
        for i in effect_set:
            effect_list.append({
                'description': i.description,
                'gold_value': None,
            })
            # gold_value += TODO

        # アイテムの価格が0Gの場合は金銭効率評価不可 → 0とする
        try:
            gold_efficiency = gold_value / item.total_cost
        except ZeroDivisionError:
            gold_efficiency = 0

        elem = {
            'name': item.name,
            'total_cost': item.total_cost,
            'gold_value': dec_round(gold_value, '0.1'),
            'stats': stats_list,
            'effects': effect_list,
            'gold_efficiency': 100 * dec_round(gold_efficiency, '0.1'),
        }

        item_list.append(elem)

    context = {
        'patch_version': patch_version,
        'item_list': item_list,
    }

    return render(request, 'gold_efficiency/index.html', context)
