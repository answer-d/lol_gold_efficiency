from django import template

register = template.Library()


@register.filter(name='lookup')
def lookup(value, arg, default=""):
    if value:
        if arg in value:
            return value[arg]
        else:
            return default
    else:
        return default


@register.filter(name='gold_value')
def gold_value(value, args):
    if args:
        return value.get_gold_value(**dict(args))
    else:
        return value.get_gold_value()


@register.filter(name='gold_efficiency')
def gold_efficiency(value, args):
    if args:
        return value.get_gold_efficiency(**dict(args))
    else:
        return value.get_gold_efficiency()
