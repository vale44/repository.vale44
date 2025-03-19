"""
    Put this script in the root folder of your repo and it will
    zip up all addon folders, create a new zip in the "generated" folder,
    and then update the md5 and addons.xml file.
"""

import hashlib
import os
import shutil
import zipfile
from xml.etree import ElementTree

SCRIPT_VERSION = 5
KODI_VERSIONS = ["krypton", "leia", "matrix", "nexus", "repo"]
IGNORE = [
    ".git",
    ".github",
    ".gitignore",
    ".DS_Store",
    "thumbs.db",
    ".idea",
    "venv",
]

def convert_bytes(num):
    """
    This function will convert bytes to MB.... GB... etc
    """
    for x in ['bytes', 'KB', 'MB', 'GB', 'TB']:
        if num < 1024.0:
            return "%3.1f %s" % (num, x)
        num /= 1024.0

class Generator:
    """
    Generates a new addons.xml file from each addon's addon.xml file
    and a new addons.xml.md5 hash file. Must be run from the root of
    the checked-out repo.
    """

    def __init__(self, release):
        self.release_path = release
        self.base_path = os.path.abspath(os.path.join(self.release_path, os.pardir))  # One level up from the release_path
        self.generated_path = os.path.join(self.base_path, "generated")
        addons_xml_path = os.path.join(self.generated_path, "addons.xml")
        md5_path = os.path.join(self.generated_path, "addons.xml.md5")

        if not os.path.exists(self.generated_path):
            os.makedirs(self.generated_path)

        self._remove_binaries()

        if self._generate_addons_file(addons_xml_path):
            if self._generate_md5_file(addons_xml_path, md5_path):
                self._copy_repository_zip_files()
                self._update_index_html()

    def _remove_binaries(self):
        """
        Removes any and all compiled Python files before operations.
        """
        for parent, dirnames, filenames in os.walk(self.release_path):
            for fn in filenames:
                if fn.lower().endswith("pyo") or fn.lower().endswith("pyc"):
                    compiled = os.path.join(parent, fn)
                    try:
                        os.remove(compiled)
                    except:
                        pass
            for dir in dirnames:
                if "pycache" in dir.lower():
                    compiled = os.path.join(parent, dir)
                    try:
                        shutil.rmtree(compiled)
                    except:
                        pass

    def _create_zip(self, folder, addon_id, version):
        """
        Creates a zip file in the "generated" directory for the given addon.
        """
        addon_folder = os.path.join(self.release_path, folder)
        zip_folder = os.path.join(self.generated_path, addon_id)
        if not os.path.exists(zip_folder):
            os.makedirs(zip_folder)

        final_zip = os.path.join(zip_folder, "{0}-{1}.zip".format(addon_id, version))
        if not os.path.exists(final_zip):
            zip = zipfile.ZipFile(final_zip, "w", compression=zipfile.ZIP_DEFLATED)
            root_len = len(os.path.dirname(os.path.abspath(addon_folder)))

            for root, dirs, files in os.walk(addon_folder):
                # remove any unneeded artifacts
                for i in IGNORE:
                    if i in dirs:
                        try:
                            dirs.remove(i)
                        except:
                            pass
                    for f in files:
                        if f.startswith(i):
                            try:
                                files.remove(f)
                            except:
                                pass

                archive_root = os.path.abspath(root)[root_len:]

                for f in files:
                    fullpath = os.path.join(root, f)
                    archive_name = os.path.join(archive_root, f)
                    zip.write(fullpath, archive_name, zipfile.ZIP_DEFLATED)

            zip.close()

    def _copy_meta_files(self, addon_id, addon_folder):
        """
        Copy the addon.xml and relevant art files into the relevant folders in the repository.
        """
        tree = ElementTree.parse(os.path.join(self.release_path, addon_id, "addon.xml"))
        root = tree.getroot()

        copyfiles = ["addon.xml"]
        for ext in root.findall("extension"):
            if ext.get("point") in ["xbmc.addon.metadata", "kodi.addon.metadata"]:
                assets = ext.find("assets")
                if not assets:
                    continue
                for art in [a for a in assets if a.text]:
                    copyfiles.append(os.path.normpath(art.text))

        src_folder = os.path.join(self.release_path, addon_id)
        for file in copyfiles:
            addon_path = os.path.join(src_folder, file)
            if not os.path.exists(addon_path):
                continue

            dest_path = os.path.join(addon_folder, file)
            asset_path = os.path.split(dest_path)[0]
            if not os.path.exists(asset_path):
                os.makedirs(asset_path)

            shutil.copy(addon_path, dest_path)

    def _generate_addons_file(self, addons_xml_path):
        """
        Generates a zip for each found addon, and updates the addons.xml file accordingly.
        """
        addons_root = ElementTree.Element('addons')
        addons_xml = ElementTree.ElementTree(addons_root)

        folders = [
            i
            for i in os.listdir(self.release_path)
            if os.path.isdir(os.path.join(self.release_path, i))
            and not i.startswith(".")
            and os.path.exists(os.path.join(self.release_path, i, "addon.xml"))
        ]

        addon_xpath = "addon[@id='{}']"
        changed = False
        for addon in folders:
            try:
                addon_xml_path = os.path.join(self.release_path, addon, "addon.xml")
                addon_xml = ElementTree.parse(addon_xml_path)
                addon_root = addon_xml.getroot()
                id = addon_root.get('id')
                version = addon_root.get('version')

                updated = False
                addon_entry = addons_root.find(addon_xpath.format(id))
                if addon_entry is not None:
                    index = addons_root.findall('addon').index(addon_entry)
                    addons_root.remove(addon_entry)
                    addons_root.insert(index, addon_root)
                    updated = True
                else:
                    addons_root.append(addon_root)
                    updated = True

                if updated:
                    # Create the zip files
                    self._create_zip(addon, id, version)
                    self._copy_meta_files(addon, os.path.join(self.generated_path, id))
                    changed = True
            except Exception as e:
                pass

        if changed:
            addons_root[:] = sorted(addons_root, key=lambda addon: addon.get('id'))
            try:
                addons_xml.write(
                    addons_xml_path, encoding="utf-8", xml_declaration=True
                )
                return changed
            except Exception as e:
                pass

    def _generate_md5_file(self, addons_xml_path, md5_path):
        """
        Generates a new addons.xml.md5 file.
        """
        try:
            with open(addons_xml_path, "r", encoding="utf-8") as f:
                m = hashlib.md5(f.read().encode("utf-8")).hexdigest()
                self._save_file(m, file=md5_path)
                return True
        except Exception as e:
            pass

    def _save_file(self, data, file):
        """
        Saves a file.
        """
        try:
            with open(file, "w") as f:
                f.write(data + "\n")
        except Exception as e:
            pass

    def _copy_repository_zip_files(self):
        """
        Copy the zip files starting with 'repository.' from the subfolders to the "generated" folder.
        """
        for root, dirs, files in os.walk(self.generated_path):
            for dir in dirs:
                if dir.startswith("repository."):
                    dir_path = os.path.join(root, dir)
                    for file in os.listdir(dir_path):
                        if file.startswith("repository.") and file.endswith(".zip"):
                            src_path = os.path.join(dir_path, file)
                            dest_path = os.path.join(self.generated_path, file)
                            try:
                                shutil.copy(src_path, dest_path)
                            except Exception as e:
                                pass

    def _update_index_html(self):
        """
        Generate or update the index.html file with the copied zip files.
        """
        index_html_path = os.path.join(self.generated_path, "index.html")
        with open(index_html_path, "w") as f:
            f.write("<!DOCTYPE html>\n")
            for file in os.listdir(self.generated_path):
                if file.endswith(".zip"):
                    f.write('<a href="{}">{}</a>\n'.format(file, file))

if __name__ == "__main__":
    for release in [r for r in KODI_VERSIONS if os.path.exists(r)]:
        Generator(release)