import mimetypes
import shutil
import tarfile
from django.http import HttpResponse
from filemanager_app.modded_filemanager import ModdedFileManager

from files3 import settings
from files3.settings import MEDIA_ROOT



# Create your views here.





# this view requires login
from django.contrib.auth.decorators import login_required


@login_required(login_url='/accounts/login/')
def filemanager_view(request, path):
    fm = ModdedFileManager(MEDIA_ROOT + '/static/filemanager/uploads/')

    return fm.render(request, path)


#override a function in allauth.account.adapter to close signup

from allauth.account.adapter import DefaultAccountAdapter

class CustomAccountAdapter(DefaultAccountAdapter):
    def is_open_for_signup(self, request):
        """
        Checks whether or not the site is open for signups.

        Next to simply returning True/False you can also intervene the
        regular flow by raising an ImmediateHttpResponse
        """
        return False