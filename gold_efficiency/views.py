from django.shortcuts import render
from .models import PatchVersion, Item
from .forms import ItemInputKeysForm
from .logger import *

# Create your views here.


@logging
def index(request):
    return render(request, 'gold_efficiency/index.html')


@logging
def itemlist(request):
    patch_version = PatchVersion.objects.order_by("-version_str").first()
    item_list = patch_version.item_set.all()

    context = {
        'patch_version': patch_version,
        'item_list': item_list,
    }

    return render(request, 'gold_efficiency/itemlist.html', context)


@logging
def itemdetail(request, item_id):
    item = Item.objects.get(pk=item_id)
    form = ItemInputKeysForm(item, request.GET)

    if not form.is_valid():
        message = "おやぁ～？インプットが不正だねぇ～？"
        return render(request, 'gold_efficiency/error.html', {"message": message})

    input_params = dict()
    for k, v in request.GET.items():
        if v:
            input_params[k] = v

    context = {
        'item': item,
        'form': form,
        'input': input_params,
    }

    return render(request, 'gold_efficiency/itemdetail.html', context)
