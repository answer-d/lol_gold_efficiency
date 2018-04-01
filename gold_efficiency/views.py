from django.shortcuts import render
from .models import PatchVersion
from .backends import RiotStaticData

# Create your views here.


def index(request):
    static_data = RiotStaticData()
    json_path = "gold_efficiency/static/gold_efficiency/json/items_ver.8.6.1_na1.json"
    items = static_data.load_from_json(json_path)
    version = "8.6.1"

    static_data.update_versions(version)
    static_data.update_stats_base(items, version)
    static_data.update_items(items, version)

    patch_version = PatchVersion.objects.get(version_str=version)
    item_list = patch_version.item_set.all()

    context = {
        'patch_version': patch_version,
        'item_list': item_list,
    }

    return render(request, 'gold_efficiency/index.html', context)
