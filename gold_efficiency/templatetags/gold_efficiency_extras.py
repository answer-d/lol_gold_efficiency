from django import template

register = template.Library()


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


@register.filter(name='is_evaluable')
def is_evaluable(value, args):
    if args:
        return value.is_evaluable(**dict(args))
    else:
        return value.is_evaluable()
