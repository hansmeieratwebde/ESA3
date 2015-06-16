from django.http import HttpResponse
from files3.settings import MEDIA_ROOT

# Create your views here.
from filemanager import FileManager


def view(request, path):
    fm = FileManager(MEDIA_ROOT+'/uploads/')
    return fm.render(request,path)

