from files3.settings import MEDIA_ROOT

# Create your views here.
from filemanager import FileManager
import os

# in this class I implement customisations on the file manager app
class ModdedFileManager(FileManager):
    def directory_structure(self):

        self.idee = 0
        dir_structure = {'': {'id': self.next_id(), 'open': 'yes', 'dirs': {}, 'files': []}}
        os.chdir(self.basepath)
        for directory, directories, files in os.walk('.'):
            #split has to be backslash on windows
            #TODO: check for OS and adapt split value
            directory_list = directory[1:].split('\\')
            current_dir = None
            nextdirs = dir_structure
            for d in directory_list:
                current_dir = nextdirs[d]
                nextdirs = current_dir['dirs']
            if directory[1:] + '/' == self.current_path:
                self.current_id = current_dir['id']
            current_dir['dirs'].update(
                dict(map(lambda d: (d, {'id': self.next_id(), 'open': 'no', 'dirs': {}, 'files': []}), directories)))
            current_dir['files'] = files
        return dir_structure


#this view requires login
from django.contrib.auth.decorators import login_required


@login_required(login_url='/accounts/login/')
def filemanager_view(request, path):
    fm = ModdedFileManager(MEDIA_ROOT + '/uploads/')

    return fm.render(request, path)

