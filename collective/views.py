from django.shortcuts import get_object_or_404, render

from .models import Collection


def collection_detail(request, slug):
    collection = get_object_or_404(Collection, slug=slug)
    artworks   = collection.get_artworks()
    return render(request, 'collective/collection.html', {
        'collection': collection,
        'artworks':   artworks,
    })
