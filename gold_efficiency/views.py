from django.shortcuts import render
from .models import Item, PatchVersion, Stats, Effect, STAB_TAGS, STAB_STATS_BASE

# Create your views here.


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
                'gold_value': STAB_STATS_BASE[i.name] * i.amount,
            })
            gold_value += STAB_STATS_BASE[i.name] * i.amount

        effect_list = list()
        for i in effect_set:
            effect_list.append({
                'description': i.description,
                'gold_value': '- ',
            })

        tmp = {
            'name': item.name,
            'total_cost': item.total_cost,
            'gold_value': gold_value,
            'stats': stats_list,
            'effects': effect_list,
            'gold_efficiency': 100*gold_value/item.total_cost,
        }

        item_list.append(tmp)

    context = {
        'item_list': item_list,
    }

    return render(request, 'gold_efficiency/index.html', context)
