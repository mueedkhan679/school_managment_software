from django import template
from apps.tenants.utils import with_tenant_prefix

register = template.Library()

@register.simple_tag(takes_context=True)
def tenant_url(context, url_name, *args, **kwargs):
    from django.urls import reverse
    request = context.get('request')
    path = reverse(url_name, args=args, kwargs=kwargs)
    return with_tenant_prefix(path, request)
