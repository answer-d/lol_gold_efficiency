from django.http import HttpResponse
from django.shortcuts import render
from .models import PatchVersion, Item
from .backends import RiotStaticData


# Create your views here.


def index(request):
    return render(request, 'gold_efficiency/index.html')


def itemlist(request):
    patch_version = PatchVersion.objects.order_by("-version_str").first()
    item_list = patch_version.item_set.all()

    context = {
        'patch_version': patch_version,
        'item_list': item_list,
    }

    return render(request, 'gold_efficiency/itemlist.html', context)


def itemdetail(request, item_id):
    # TODO:インプットのヴァリデーション

    item = Item.objects.get(pk=item_id)
    input_params = dict()
    for k, v in request.GET.items():
        if v:
            input_params[k] = v

    context = {
        'item': item,
        'input': input_params,
    }

    return render(request, 'gold_efficiency/itemdetail.html', context)
