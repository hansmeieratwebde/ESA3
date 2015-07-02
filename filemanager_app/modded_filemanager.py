from filemanager import FileManager, settings
import mimetypes
import shutil
import tarfile
from django.http import HttpResponse
import os, re
from django.core.servers.basehttp import FileWrapper
from sys import platform



from easy_thumbnails.files import get_thumbnailer
import files3
from files3.settings import MEDIA_ROOT




# in this class I implement customisations on the file manager app

class ModdedFileManager(FileManager):
    
    
    def get_file_extension(self, file):
        # check for jpg extension
        ext = file[file.rfind('.'):]
        ext = ext[1:].lower()#remove dot and force lowercase
        return ext

    def create_thumbnails(self, directory, files):
        """
        checks for image files and creates thumbnails with easy_thumbnails package
        #params: path to directory, list with files in that directory
        :rtype : none
        """
        for file in files:
            ext = self.get_file_extension(file)
            if ext == 'jpg':
                try:
                    thumbnailer = get_thumbnailer(MEDIA_ROOT + '/static/filemanager/uploads' + directory + '/' + file)

                    thumbnail_options = {'crop': True}
                    for size in (120, 240):
                        thumbnail_options.update({'size': (size, size)})
                        thumbnailer.get_thumbnail(thumbnail_options)
                except IOError:
                    pass

    def delete_thumbnails(self, path, filename):
        """deletes thumbnails in thumbnails subdirectory, is called when a jpg file is deleted

        :param path:
        :param filename:
        :return: none
        """
        try:
            os.chdir (self.basepath+path+'/thumbnails')
            os.remove(filename+'.240x240_q85_crop.jpg')
            os.remove(filename+'.120x120_q85_crop.jpg')
        except IOError:
           return 'Could not remove thumbnails'


    #overrides method of superclass, changed: files should be opened as binary files, otherwise it won't work under windows
    def handle_form(self, form, files):
        action = form.cleaned_data['action']
        path = form.cleaned_data['path']
        name = form.cleaned_data['name']
        ufile = form.cleaned_data['ufile']
        file_or_dir = form.cleaned_data['file_or_dir']
        self.current_path = form.cleaned_data['current_path']
        messages = []
        if name and file_or_dir == 'dir' and not re.match(r'[\w\d_ -]+', name).group(0) == name:
            messages.append("Invalid folder name : " + name)
            return messages
        if name and file_or_dir == 'file' and (
            re.search('\.\.', name) or not re.match(r'[\w\d_ -.]+', name).group(0) == name):
            messages.append("Invalid file name : " + name)
            return messages
        if not re.match(r'[\w\d_ -/]+', path).group(0) == path:
            messages.append("Invalid path : " + path)
            return messages
        if action == 'upload':
            for f in files.getlist('ufile'):
                if re.search('\.\.', f.name) or not re.match('[\w\d_ -/.]+', f.name).group(0) == f.name:
                    #TODO: This throws an encoding error with Umlauts in file names although the Encoding seems to be Unicode

                    messages.append("File name is not valid")#removed f.name here due to encoding error
                elif f.size > self.maxfilesize * 1024:
                    messages.append("File size exceeded " + str(self.maxfilesize) + " KB : " + f.name)
                elif (settings.FILEMANAGER_CHECK_SPACE and
                          ((self.get_size(self.basepath) + f.size) > self.maxspace * 1024)):
                    messages.append("Total Space size exceeded " + str(self.maxspace) + " KB : " + f.name)
                elif self.extensions and len(f.name.split('.')) > 1 and f.name.split('.')[-1] not in self.extensions:
                    messages.append("File extension not allowed (." + f.name.split('.')[-1] + ") : " + f.name)
                elif self.extensions and len(f.name.split('.')) == 1 and f.name.split('.')[-1] not in self.extensions:
                    messages.append("No file extension in uploaded file : " + f.name)
                else:
                    filepath = self.basepath + path + self.rename_if_exists(self.basepath + path, f.name)
                    with open(filepath, 'wb') as dest:
                        for chunk in f.chunks():
                            dest.write(chunk)
                    f.close()
            if len(messages) == 0:
                messages.append('All files uploaded successfully')
        elif action == 'add':
            os.chdir(self.basepath)
            no_of_folders = len(list(os.walk('.')))
            if (no_of_folders + 1) <= self.maxfolders:
                try:
                    os.chdir(self.basepath + path)
                    os.mkdir(name)
                    messages.append('Folder created successfully : ' + name)
                except:
                    messages.append('Folder couldn\'t be created : ' + name)
            else:
                messages.append(
                    'Folder couldn\' be created because maximum number of folders exceeded : ' + str(self.maxfolders))
        elif action == 'rename' and file_or_dir == 'dir':
            oldname = path.split('/')[-2]
            path = '/'.join(path.split('/')[:-2])
            try:
                os.chdir(self.basepath + path)
                os.rename(oldname, name)
                messages.append('Folder renamed successfully from ' + oldname + ' to ' + name)
            except:
                messages.append('Folder couldn\'t renamed to ' + name)
        elif action == 'delete' and file_or_dir == 'dir':
            if path == '/':
                messages.append('root folder can\'t be deleted')
            else:
                name = path.split('/')[-2]
                path = '/'.join(path.split('/')[:-2])
                try:
                    os.chdir(self.basepath + path)
                    shutil.rmtree(name)
                    messages.append('Folder deleted successfully : ' + name)
                except:
                    messages.append('Folder couldn\'t deleted : ' + name)
        elif action == 'rename' and file_or_dir == 'file':
            oldname = path.split('/')[-1]
            old_ext = oldname.split('.')[1] if len(oldname.split('.')) > 1 else None
            new_ext = name.split('.')[1] if len(name.split('.')) > 1 else None
            if old_ext == new_ext:
                path = '/'.join(path.split('/')[:-1])
                try:
                    os.chdir(self.basepath + path)
                    os.rename(oldname, name)
                    messages.append('File renamed successfully from ' + oldname + ' to ' + name)
                except:
                    messages.append('File couldn\'t be renamed to ' + name)
            else:
                if old_ext:
                    messages.append('File extension should be same : .' + old_ext)
                else:
                    messages.append('New file extension didn\'t match with old file extension')
        elif action == 'delete' and file_or_dir == 'file':
            if path == '/':
                messages.append('root folder can\'t be deleted')
            else:
                name = path.split('/')[-1]
                path = '/'.join(path.split('/')[:-1])
                try:
                    os.chdir(self.basepath + path)
                    os.remove(name)

                    # if jpg, delete thumbnails
                    if self.get_file_extension(name) == 'jpg':
                      self.delete_thumbnails (path, name)

                    messages.append('File deleted successfully : ' + name)
                except:
                    messages.append('File couldn\'t be deleted : ' + name)
        elif action == 'move' or action == 'copy':
            # from path to current_path
            if self.current_path.find(path) == 0:
                messages.append('Cannot move/copy to a child folder')
            else:
                path = os.path.normpath(path)  # strip trailing slash if any
                if os.path.exists(self.basepath + self.current_path + os.path.basename(path)):
                    messages.append('ERROR: A file/folder with this name already exists in the destination folder.')
                else:
                    if action == 'move':
                        method = shutil.move
                    else:
                        if file_or_dir == 'dir':
                            method = shutil.copytree
                        else:
                            method = shutil.copy
                    try:
                        method(self.basepath + path, self.basepath + self.current_path + os.path.basename(path))
                    except:
                        messages.append('File/folder couldn\'t be moved/copied.')
        return messages

    #overrides method of superclass
    #makes it work on windows systems
    #includes a function call for thumbnail creation
    def directory_structure(self):

        self.idee = 0
        dir_structure = {'': {'id': self.next_id(), 'open': 'yes', 'dirs': {}, 'files': []}}
        os.chdir(self.basepath)
        for directory, directories, files in os.walk('.'):

            # split has to be backslash on windows
            #check for OS and adapt split value
            if platform == "win32":
                directory_list = directory[1:].split('\\')
            else:
                directory_list = directory[1:].split('/')

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
            #check for image files and create thumbnail if necessary
            if  directory.rfind(files3.settings.THUMBNAIL_SUBDIR) == -1:#do not create thumbnails of files in thumbnails directory
                self.create_thumbnails(directory[1:], files)

        return dir_structure



    #changed: all files should be downloaded as binaries, otherwise it won't work under windows
    def download(self, path, file_or_dir):
        if not re.match(r'[\w\d_ -/]*', path).group(0) == path:
            return HttpResponse('Invalid path')
        if file_or_dir == 'file':
            filepath = self.basepath + '/' + path
            wrapper = FileWrapper(file(filepath, ('rb')))
            response = HttpResponse(wrapper, content_type=mimetypes.guess_type(filepath)[0])
            response['Content-Length'] = os.path.getsize(filepath)
            response['Content-Disposition'] = 'attachment; filename=' + path.split('/')[-1]
            return response
        elif file_or_dir == 'dir':
            dirpath = self.basepath + '/' + path
            dirname = dirpath.split('/')[-2]
            response = HttpResponse(content_type='application/x-gzip')
            response['Content-Disposition'] = 'attachment; filename=%s.tar.gz' % dirname
            tarred = tarfile.open(fileobj=response, mode='w:gz')
            tarred.add(dirpath, arcname=dirname)
            tarred.close()
            return response


