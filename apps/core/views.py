from django.shortcuts import render


def index(request):
    """Landing page shown before login (Phase 1 placeholder).

    Phase 2 will replace this with the admin authentication flow.
    """
    return render(request, "core/index.html")

