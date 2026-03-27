import tkinter as tk
from tkinter import messagebox, scrolledtext
import xml.etree.ElementTree as ET
import ctypes
import json
import os
import glob
import shutil

# Hide the Python console
ctypes.windll.user32.ShowWindow(ctypes.windll.kernel32.GetConsoleWindow(), 0)

# Function to load XML and get current values
def load_xml():
    repo_path = glob.glob('repo/repository.*/addon.xml')
    if not repo_path:
        return None, None, None, None
    tree = ET.parse(repo_path[0])
    root = tree.getroot()
    datadir = root.find(".//dir/datadir").text
    # Extract the repository name from the datadir link
    gitrepo = datadir.split('/')[-4]
    data = {
        'USERNAME': root.attrib.get('provider-name', '*USERNAME'),
        'GITREPO': gitrepo,
        'KODIREPONAME': root.attrib.get('name', '*KODIREPONAME'),
        'VERSION': root.attrib.get('version', '1.0'),
        'DESCRIPTION': root.find(".//description").text or '*DESCRIPTION'
    }
    return data, tree, root, repo_path[0]

# Function to create a new addon.xml
def create_addon_xml(data, repo_path, window_size="800x300"):
    addon_id = data['GITREPO']
    if addon_id.startswith("repository."):
        addon_id = addon_id[len("repository."):]
    addon_xml_content = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<addon id="repository.{addon_id}" name="{data['KODIREPONAME']}" version="{data['VERSION']}" provider-name="{data['USERNAME']}">
    <extension point="xbmc.addon.repository" name="{data['KODIREPONAME']}">
        <dir>
            <info compressed="false">https://raw.githubusercontent.com/{data['USERNAME']}/{data['GITREPO']}/main/generated/addons.xml</info>
            <checksum>https://raw.githubusercontent.com/{data['USERNAME']}/{data['GITREPO']}/main/generated/addons.xml.md5</checksum>
            <datadir zip="true">https://raw.githubusercontent.com/{data['USERNAME']}/{data['GITREPO']}/main/generated/</datadir>
        </dir>
    </extension>
    <extension point="xbmc.addon.metadata">
        <summary>{data['KODIREPONAME']}</summary>
        <description>{data['DESCRIPTION']}</description>
        <disclaimer></disclaimer>
        <platform>all</platform>
        <assets>
            <icon>icon.png</icon>
            <fanart>fanart.jpg</fanart>
        </assets>
    </extension>
    <!-- window_size: {window_size} -->
</addon>
"""
    with open(repo_path, 'w') as file:
        file.write(addon_xml_content)

# Function to save changes to XML
def save_xml(data, tree, root, repo_path):
    addon_id = data['GITREPO']
    if addon_id.startswith("repository."):
        addon_id = addon_id[len("repository."):]
    window_size = root_window.geometry()
    if not repo_path or not os.path.exists(repo_path):
        repo_folder = f'repo/repository.{addon_id}'
        os.makedirs(repo_folder, exist_ok=True)
        repo_path = os.path.join(repo_folder, 'addon.xml')
        create_addon_xml(data, repo_path, window_size)
    else:
        root.set('provider-name', data['USERNAME'])
        root.set('id', f"repository.{addon_id}")
        root.set('name', data['KODIREPONAME'])
        root.set('version', data['VERSION'])
        
        for element in root.findall(".//extension[@point='xbmc.addon.repository']"):
            element.set('name', data['KODIREPONAME'])
        
        root.find(".//description").text = data['DESCRIPTION']
        
        for element in root.findall(".//dir/info"):
            element.text = f"https://raw.githubusercontent.com/{data['USERNAME']}/{data['GITREPO']}/main/generated/addons.xml"
        
        for element in root.findall(".//dir/checksum"):
            element.text = f"https://raw.githubusercontent.com/{data['USERNAME']}/{data['GITREPO']}/main/generated/addons.xml.md5"
        
        for element in root.findall(".//dir/datadir"):
            element.text = f"https://raw.githubusercontent.com/{data['USERNAME']}/{data['GITREPO']}/main/generated/"
        
        for element in root.findall(".//summary"):
            element.text = data['KODIREPONAME']
        
        tree.write(repo_path)

    # Rename the subfolder
    subfolder_path = os.path.dirname(repo_path)
    new_subfolder_name = f"repository.{addon_id}"
    new_subfolder_path = os.path.join('repo', new_subfolder_name)
    if subfolder_path != new_subfolder_path:
        shutil.move(subfolder_path, new_subfolder_path)

# Function to handle submit button
def on_submit():
    data = {
        'USERNAME': entry_username.get(),
        'GITREPO': entry_gitrepo.get(),
        'KODIREPONAME': entry_kodireponame.get(),
        'VERSION': entry_version.get(),
        'DESCRIPTION': text_description.get("1.0", tk.END).strip()
    }
    
    if all(data.values()):
        save_xml(data, tree, root, repo_path)
        messagebox.showinfo("Success", "addon.xml updated successfully!")
        save_window_size()
        root_window.destroy()
    else:
        messagebox.showwarning("Warning", "All fields must be filled out.")

# Function to load window size from settings
def load_window_size():
    settings_file = '1. Repository Configurator Window Size.json'
    if os.path.exists(settings_file):
        with open(settings_file, 'r') as f:
            settings = json.load(f)
            return settings.get("window_size", "800x300")
    return "800x300"

# Function to save window size to settings
def save_window_size():
    settings_file = '1. Repository Configurator Window Size.json'
    if root_window.geometry() != "800x300":
        settings = {"window_size": root_window.geometry()}
        with open(settings_file, 'w') as f:
            json.dump(settings, f)

# Load current XML data
data, tree, root, repo_path = load_xml()
if data is None:
    data = {
        'USERNAME': '*USERNAME',
        'GITREPO': 'example',
        'KODIREPONAME': '*KODIREPONAME',
        'VERSION': '1.0',
        'DESCRIPTION': '*DESCRIPTION'
    }
    repo_path = f'repo/repository.{data["GITREPO"]}/addon.xml'
    os.makedirs(os.path.dirname(repo_path), exist_ok=True)
    create_addon_xml(data, repo_path)
    data, tree, root, repo_path = load_xml()  # Reload the XML after creating it

# Create main window
root_window = tk.Tk()
root_window.title("Repository Configurator")
root_window.geometry(load_window_size())
root_window.minsize(735, 300)  # Updated minimum width to 735 pixels
root_window.resizable(True, True)

# Set a modern-looking font
font = ("Helvetica", 10)  # Fixed font size

# Create a master frame to hold all other frames
master_frame = tk.Frame(root_window)
master_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

# Create frames to separate input boxes and description box
input_frame = tk.Frame(master_frame, width=250)  # Reduced width
input_frame.pack(fill=tk.BOTH, side=tk.LEFT, expand=True, padx=5, pady=5)

description_frame = tk.Frame(master_frame, width=350)  # Reduced width
description_frame.pack(fill=tk.BOTH, side=tk.RIGHT, expand=True, padx=5, pady=5)

# Create and place labels and entry widgets in input_frame
label_username = tk.Label(input_frame, text="Your Github Username:", font=font, anchor='w')
label_username.grid(row=0, column=0, sticky='w', padx=5, pady=2)
entry_username = tk.Entry(input_frame, font=font)
entry_username.grid(row=0, column=1, padx=5, pady=2, sticky='ew')

if data['USERNAME'] != '*USERNAME':
    entry_username.insert(0, data['USERNAME'])

label_gitrepo = tk.Label(input_frame, text="What you named your Repository on Github:", font=font, anchor='w')
label_gitrepo.grid(row=1, column=0, sticky='w', padx=5, pady=2)
entry_gitrepo = tk.Entry(input_frame, font=font)
entry_gitrepo.grid(row=1, column=1, padx=5, pady=2, sticky='ew')

if data['GITREPO'] != '*GITREPO':
    entry_gitrepo.insert(0, data['GITREPO'])

label_kodireponame = tk.Label(input_frame, text="The name of your Repository in Kodi:", font=font, anchor='w')
label_kodireponame.grid(row=2, column=0, sticky='w', padx=5, pady=2)
entry_kodireponame = tk.Entry(input_frame, font=font)
entry_kodireponame.grid(row=2, column=1, padx=5, pady=2, sticky='ew')

if data['KODIREPONAME'] != '*KODIREPONAME':
    entry_kodireponame.insert(0, data['KODIREPONAME'])

label_version = tk.Label(input_frame, text="The Version of your Kodi Repository,\nupdate it when you make changes:", font=font, anchor='w')
label_version.grid(row=3, column=0, sticky='w', padx=5, pady=2)
entry_version = tk.Entry(input_frame, font=font)
entry_version.grid(row=3, column=1, padx=5, pady=2, sticky='ew')

if data['VERSION'] != '*VERSION':
    entry_version.insert(0, data['VERSION'])
else:
    entry_version.insert(0, '1.0')

# Create and place description box in description_frame
label_description = tk.Label(description_frame, text="The Description of your Repository in Kodi:", font=font, anchor='w')
label_description.grid(row=0, column=0, sticky='nw', padx=5, pady=2)
text_description = scrolledtext.ScrolledText(description_frame, font=font, wrap=tk.WORD, height=10)
text_description.grid(row=1, column=0, padx=5, pady=2, sticky='nsew')

if data['DESCRIPTION'] != '*DESCRIPTION':
    text_description.insert(tk.INSERT, data['DESCRIPTION'])

# Create and place submit button below the frames
submit_button = tk.Button(root_window, text="Save", command=on_submit, font=font, bg="#4CAF50", fg="white")
submit_button.pack(side=tk.BOTTOM, pady=10)

# Make columns and rows resizable
input_frame.grid_columnconfigure(0, weight=1)
input_frame.grid_columnconfigure(1, weight=2)
input_frame.grid_rowconfigure(0, weight=1)
input_frame.grid_rowconfigure(1, weight=1)
input_frame.grid_rowconfigure(2, weight=1)
input_frame.grid_rowconfigure(3, weight=1)

description_frame.grid_columnconfigure(0, weight=1)
description_frame.grid_rowconfigure(0, weight=1)
description_frame.grid_rowconfigure(1, weight=3)

# Start the Tkinter event loop
root_window.mainloop()