import tkinter as tk
from tkinter import messagebox
import os
import xml.etree.ElementTree as ET
import sys
import ctypes
import re
import xml.dom.minidom as minidom

# Hide console on Windows
if sys.platform == "win32":
    ctypes.windll.kernel32.FreeConsole()

# Locate repository folder and addon.xml
script_dir = os.path.dirname(os.path.abspath(__file__))
repo_dir = os.path.join(script_dir, "repo")

repository_folder = None
addon_xml_path = None
names_txt_path = None

if os.path.exists(repo_dir):
    for folder in os.listdir(repo_dir):
        if folder.startswith("repository."):
            repository_folder = os.path.join(repo_dir, folder)
            addon_xml_candidate = os.path.join(repository_folder, "addon.xml")
            if os.path.exists(addon_xml_candidate):
                addon_xml_path = addon_xml_candidate
                names_txt_path = os.path.join(repository_folder, "Add-on Repository Names.txt")
                break

if not addon_xml_path:
    messagebox.showerror("Error", "No addon.xml found in a 'repository.' folder inside 'repo'. Exiting.")
    sys.exit()

# Function to clean clipboard input
def clean_pasted_content(content):
    lines = content.strip().splitlines()
    return "\n".join(line.lstrip() for line in lines)

# Function to check if a <dir> entry already exists
def dir_exists(extension, info, checksum, datadir):
    for dir_elem in extension.findall("dir"):
        info_elem = dir_elem.find("info")
        checksum_elem = dir_elem.find("checksum")
        datadir_elem = dir_elem.find("datadir")

        if (
            info_elem is not None and info_elem.text == info and
            checksum_elem is not None and checksum_elem.text == checksum and
            datadir_elem is not None and datadir_elem.text == datadir
        ):
            return True
    return False

# Function to pretty-print XML with minimal unnecessary newlines
def pretty_print_xml(xml_string):
    dom = minidom.parseString(xml_string)
    pretty_xml = dom.toprettyxml(indent="    ")

    # Remove unnecessary newlines in between tags
    pretty_xml = re.sub(r'\n\s*\n', '\n', pretty_xml)  # Remove empty lines between tags
    return pretty_xml

# Save function updated with pretty formatting
def save_repositories():
    if not addon_xml_path or not os.path.exists(addon_xml_path):
        messagebox.showerror("Error", "No valid addon.xml found.")
        return

    try:
        tree = ET.parse(addon_xml_path)
        root = tree.getroot()

        extension = root.find("extension[@point='xbmc.addon.repository']")
        if extension is None:
            messagebox.showerror("Error", "Invalid addon.xml structure (No extension point).")
            return

        added = False
        removed = False
        name_changed = False

        # Check each entry in the GUI to add or remove from XML
        for i, (links_entry, name_entry) in enumerate(entries):
            links_text = links_entry.get("1.0", tk.END).strip()
            links = extract_links(links_text)

            if not links:
                continue

            info, checksum, datadir = links

            # Check if the entry already exists
            if dir_exists(extension, info, checksum, datadir):
                # Check if the name has changed
                if name_entry.get() != previous_names[i]:
                    name_changed = True
                continue

            # Create new <dir> element if not found
            new_dir = ET.Element("dir")
            ET.SubElement(new_dir, "info", {"compressed": "false"}).text = info
            ET.SubElement(new_dir, "checksum").text = checksum
            ET.SubElement(new_dir, "datadir", {"zip": "true"}).text = datadir

            # Append the new <dir> entry
            extension.append(new_dir)
            added = True

        # Check for entries to remove
        existing_dirs = extension.findall("dir")
        for dir_elem in existing_dirs[1:]:  # Skip the first <dir> entry (main script)
            info = dir_elem.find("info").text
            checksum = dir_elem.find("checksum").text
            datadir = dir_elem.find("datadir").text

            # If an entry is no longer in the GUI, remove it from XML
            if not any(info in entry.get("1.0", tk.END) for entry, _ in entries):
                extension.remove(dir_elem)
                removed = True

        if added or removed or name_changed:
            # Convert the tree to a string, then pretty-print the XML
            xml_str = ET.tostring(root, encoding='utf-8', method='xml').decode('utf-8')
            formatted_xml = pretty_print_xml(xml_str)
            
            # Write the formatted XML back to the file
            with open(addon_xml_path, "w", encoding="utf-8") as f:
                f.write(formatted_xml)
            
            # Save names in a text file
            save_repository_names()

            messagebox.showinfo("Success", "Repositories saved successfully!")
        else:
            messagebox.showinfo("Info", "No changes detected.")

    except Exception as e:
        messagebox.showerror("Error", f"Failed to save: {str(e)}")

# Function to save repository names to the text file
def save_repository_names():
    try:
        with open(names_txt_path, "w", encoding="utf-8") as f:
            for _, name_entry in entries:
                f.write((name_entry.get() if name_entry.get() else "") + "\n")
    except Exception as e:
        messagebox.showerror("Error", f"Failed to save repository names: {str(e)}")

# Function to add repository entry
def add_repository_entry(info="", checksum="", datadir=""):
    entry_frame = tk.Frame(entries_frame, padx=10, pady=5, relief="solid", borderwidth=1, bg="white", width=600)
    entry_frame.pack(fill='x', padx=10, pady=5)

    # Label for optional name
    name_label = tk.Label(entry_frame, text="Optional Name", font=('Arial', 10, 'bold'), bg="white", fg="black")
    name_label.pack(anchor="center", padx=5, pady=2)  # Centered above the input box

    # Text box for entering optional name
    name_entry = tk.Entry(entry_frame, font=('Arial', 10), width=50, relief="solid", borderwidth=1, justify='center')
    name_entry.pack(padx=5, pady=2)

    # Align the label above the input box
    links_label = tk.Label(entry_frame, text="Repository Links (Info, Checksum, Datadir)", font=('Arial', 10, 'bold'), bg="white", fg="black")
    links_label.pack(anchor="center", padx=5, pady=2)  # Centered above the input box

    # Add the optional name field to the entry frame
    links_entry = tk.Text(entry_frame, font=('Arial', 10), wrap="word", height=4, width=98, relief="solid", borderwidth=1)
    links_entry.pack(padx=5, pady=2)

    # If info, checksum, and datadir are provided, set them as the text in the links_entry
    if info and checksum and datadir:
        links_entry.insert(tk.END, f"{info}\n{checksum}\n{datadir}")

    def remove_entry():
        entries.remove((links_entry, name_entry))
        previous_names.remove(name_entry.get())  # Remove the name from the previous names list
        entry_frame.destroy()
        update_scroll_region()

    remove_button = tk.Button(entry_frame, text="Remove", command=remove_entry, bg="red", fg="white", font=('Arial', 10, 'bold'), relief="solid", borderwidth=1)
    remove_button.pack(anchor="e", padx=5, pady=5)

    def on_right_click_links(event):
        links_context_menu.post(event.x_root, event.y_root)

    def paste_links():
        try:
            clipboard_content = root.clipboard_get()
            clipboard_content = clean_pasted_content(clipboard_content)
            links_entry.delete(1.0, tk.END)
            links_entry.insert(tk.END, clipboard_content)
        except tk.TclError:
            messagebox.showerror("Error", "Clipboard is empty or invalid.")

    links_context_menu = tk.Menu(root, tearoff=0)
    links_context_menu.add_command(label="Paste", command=paste_links)

    links_entry.bind("<Button-3>", on_right_click_links)

    entries.append((links_entry, name_entry))
    previous_names.append(name_entry.get())  # Add the initial name to the previous names list
    update_scroll_region()

# Function to update scroll region
def update_scroll_region():
    canvas_height = 530 + len(entries) * 200
    canvas.config(scrollregion=(0, 0, 780, canvas_height))
    if len(entries) <= 2:
        scrollbar.pack_forget()
    else:
        scrollbar.pack(side="right", fill="y")

# Function to extract links (info, checksum, datadir)
def extract_links(content):
    print("Clipboard content:")
    print(content)  # Print the raw content for debugging

    # Remove all XML/HTML-like tags to isolate the URLs
    cleaned_content = re.sub(r'<.*?>', '', content)  # This removes any tags (like <info>, <checksum>, etc.)
    print("Cleaned content (just links):")
    print(cleaned_content)

    # Use regex to find links that start with "http"
    links = re.findall(r'http[^\s<>]+', cleaned_content)

    print("Extracted links:", links)

    # Check if we found exactly 3 links
    if len(links) != 3:
        messagebox.showerror("Error", "Clipboard must contain exactly 3 valid links: Info, Checksum, and Datadir.")
        return None

    # Find the correct links based on pattern
    info = next((link for link in links if link.endswith('.xml')), None)
    checksum = next((link for link in links if re.search(r'addons\.xml\.', link)), None)
    datadir = next((link for link in links if not link.endswith('.xml') and not re.search(r'addons\.xml\.', link)), None)

    # If any of the links are not found, return an error
    if not all([info, checksum, datadir]):
        messagebox.showerror("Error", "Links are incomplete or not properly formatted.")
        return None

    return info, checksum, datadir

# Function to load existing repository entries and names from the XML file and names text file
def load_existing_entries():
    try:
        tree = ET.parse(addon_xml_path)
        root = tree.getroot()

        extension = root.find("extension[@point='xbmc.addon.repository']")
        if extension is None:
            return

        existing_dirs = extension.findall("dir")

        # Skip the first <dir> entry (main script)
        for dir_elem in existing_dirs[1:]:
            info = dir_elem.find("info").text
            checksum = dir_elem.find("checksum").text
            datadir = dir_elem.find("datadir").text

            # Add the loaded entry
            add_repository_entry(info, checksum, datadir)

        # Load names from text file if it exists
        if os.path.exists(names_txt_path):
            with open(names_txt_path, "r", encoding="utf-8") as f:
                for i, line in enumerate(f):
                    if i < len(entries):
                        entries[i][1].insert(0, line.strip())
                        previous_names.append(line.strip())
                    else:
                        entry_names.append(tk.Entry(entries_frame, font=('Arial', 10), width=50, relief="solid", borderwidth=1))
                        entry_names[-1].insert(0, line.strip())
                        previous_names.append(line.strip())

    except Exception as e:
        messagebox.showerror("Error", f"Failed to load existing entries: {str(e)}")

# Setup GUI
root = tk.Tk()
root.title("Add Add-on Repository Entries")
root.geometry("780x510")
root.minsize(780, 510)
root.configure(bg="#D9EAFD")

main_frame = tk.Frame(root, bg="#D9EAFD")
main_frame.pack(fill="both", expand=True)

canvas = tk.Canvas(main_frame, highlightthickness=1, bg="#D9EAFD", bd=1, relief="solid")
scrollbar = tk.Scrollbar(main_frame, orient='vertical', command=canvas.yview)
scrollable_frame = tk.Frame(canvas, bg="#D9EAFD")

canvas.create_window((0, 0), window=scrollable_frame, anchor="nw", width=760)
canvas.configure(yscrollcommand=scrollbar.set)

canvas.pack(side="left", fill="both", expand=True)
scrollbar.pack(side="right", fill="y")

title_label = tk.Label(scrollable_frame, text="Add Add-on Repository Entries", font=('Arial', 14, 'bold'), bg="#D9EAFD", fg="black")
title_label.pack(pady=(10, 5))

button_frame = tk.Frame(scrollable_frame, bg="#D9EAFD")
button_frame.pack(fill="x", padx=10, pady=5)

add_button = tk.Button(button_frame, text="Add Repository", command=add_repository_entry, bg="green", fg="white", font=('Arial', 10, 'bold'), relief="solid", borderwidth=1)
add_button.pack(side="left", padx=5, pady=5)

save_button = tk.Button(button_frame, text="Save Repositories", command=save_repositories, bg="blue", fg="white", font=('Arial', 10, 'bold'), relief="solid", borderwidth=1)
save_button.pack(side="right", padx=5, pady=5)

entries_frame = tk.Frame(scrollable_frame, bg="#D9EAFD")
entries_frame.pack(fill="both", expand=True)

# Initialize at least one entry if none exist
entries = []
entry_names = []
previous_names = []
load_existing_entries()
update_scroll_region()

canvas.bind_all("<MouseWheel>", lambda event: canvas.yview_scroll(-1 * (event.delta // 120), "units"))

root.mainloop()