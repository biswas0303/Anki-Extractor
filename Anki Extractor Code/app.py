import customtkinter as ctk
from tkinter import filedialog
import os
import zipfile
import sqlite3
import pdfkit
import json
import re
from PIL import Image
import threading


class AnkiExtractorApp:

    def __init__(self):
        # Theme setup
        ctk.set_appearance_mode("System")
        ctk.set_default_color_theme("blue")

        # Main window
        self.app = ctk.CTk()
        self.app.title("Anki Extractor")
        self.app.geometry("700x450")
        self.app.resizable(False, False)

        # Variables
        self.apkg_path = ctk.StringVar()
        self.export_path = ctk.StringVar()

        #for threading
        self.cancel_flag = False
        self.worker_thread = None
        self.total_notes = 0
        self.processed_notes = 0

        # Build UI
        self.create_widgets()

        self.app.protocol("WM_DELETE_WINDOW", self.on_close)

    # ---------------- UI ----------------

    def create_widgets(self):
        # Title
        self.title = ctk.CTkLabel(
            self.app,
            text="Anki Extractor",
            font=("Arial", 26, "bold")
        )
        self.title.pack(pady=20)

        # ---------------- APKG Selection ----------------
        self.frame1 = ctk.CTkFrame(self.app, fg_color="transparent")
        self.frame1.pack(fill="x", padx=20)

        self.apkg_entry = ctk.CTkEntry(self.frame1, width=480, textvariable=self.apkg_path)
        self.apkg_entry.pack(side="left", padx=(0, 10))

        self.browse1 = ctk.CTkButton(
            self.frame1,
            text="Browse",
            width=100,
            command=self.browse_apkg
        )
        self.browse1.pack(side="left")

        # ---------------- Export Location ----------------
        self.apkg_export_label = ctk.CTkLabel(
            self.app,
            text="Extracted Location:",
            font=("Arial", 14, "bold")
        )
        self.apkg_export_label.pack(anchor="w", padx=20, pady=(20, 5))

        self.frame2 = ctk.CTkFrame(self.app, fg_color="transparent")
        self.frame2.pack(fill="x", padx=20)

        self.export_entry = ctk.CTkEntry(self.frame2, width=480, textvariable=self.export_path)
        self.export_entry.pack(side="left", padx=(0, 10))

        self.browse2 = ctk.CTkButton(
            self.frame2,
            text="Browse",
            width=100,
            command=self.browse_export
        )
        self.browse2.pack(side="left")

        # ---------------- Action Buttons ----------------
        self.action_frame = ctk.CTkFrame(self.app, fg_color="transparent")
        self.action_frame.pack(pady=25)

        # Execute Button
        self.execute_btn = ctk.CTkButton(
            self.action_frame,
            text="Execute",
            width=100,
            height=40,
            command=self.start_execute_thread
        )
        self.execute_btn.pack(side="left", padx=2)

        # Extract Data Button
        self.extract_btn = ctk.CTkButton(
            self.action_frame,
            text="Extract Database",
            width=100,
            height=40,
            command=self.start_extract_thread
        )
        self.extract_btn.pack(side="left", padx=2)

        # Cancel Button
        self.cancel_btn = ctk.CTkButton(
            self.action_frame,
            text="Cancel",
            width=100,
            height=40,
            fg_color="red",
            command=self.cancel_operation
        )
        self.cancel_btn.pack(side = "left", padx=50)

        self.progress_bar = ctk.CTkProgressBar(self.app, width=600)
        self.progress_bar.pack(padx=20, pady=(0, 10))
        self.progress_bar.set(0)

        # ---------------- Log Box ----------------
        self.log_box = ctk.CTkTextbox(
            self.app,
            width=600,
            height=120
        )
        self.log_box.pack(fill="both", expand=True, padx=20, pady=(0, 20))
        self.log_box.configure(state="disabled")

    # ---------------- Functions ----------------

    def log(self, message):
        self.app.after(0, self._append_log, message)

    def _append_log(self, message):
        self.log_box.configure(state="normal")
        self.log_box.insert("end", message + "\n")
        self.log_box.see("end")
        self.log_box.configure(state="disabled")

    def update_progress(self, current, total):
        progress = current / total if total > 0 else 0
        self.app.after(0, lambda: self.progress_bar.set(progress))
        
    def cancel_operation(self):
        self.cancel_flag = True
        self.log("Cancellation requested...")
        
    def browse_apkg(self):
        filename = filedialog.askopenfilename(
            title="Select Anki Package",
            filetypes=[("Anki Package", "*.apkg")]
        )

        if filename:
            self.apkg_path.set(filename)
            self.log(f"APKG selected: {filename}")

    def browse_export(self):
        folder = filedialog.askdirectory(
            title="Select Export Folder"
        )

        if folder:
            self.export_path.set(folder)
            self.log(f"Export folder selected: {folder}")

    def execute(self):
        
        if self.cancel_flag:
            self.log("Operation cancelled.")
            return
        
        # if path are empty, log and return
        if self.apkg_entry.get() == "" or self.export_entry.get() == "":
            self.log("Please select both APKG file and export location.")
            return
        
        # Check if export folder is empty
        if os.path.exists(self.export_path.get()) and os.listdir(self.export_path.get()):
            self.log("Export folder is not empty. Please select an empty folder.")
            return
        
        self.log("Starting extraction...")
        self.log(f"APKG: {self.apkg_path.get()}")
        self.log(f"Export: {self.export_path.get()}")

        with zipfile.ZipFile(self.apkg_path.get(), "r") as zip_ref:
            files = zip_ref.namelist()
            total_files = len(files)

            for i, file in enumerate(files, start=1):
                if self.cancel_flag:
                    self.log("Extraction cancelled.")
                    self.app.after(0, lambda: self.progress_bar.set(0))
                    return

                zip_ref.extract(file, self.export_path.get())
                self.update_progress(i, total_files)
        
        self.log("Extraction completed successfully.")
        self.log(f"Files extracted to: {self.export_path.get()}")
        self.log(f"Total files extracted: {zip_ref.namelist()}")
        self.log(f"Total files extracted: {len(zip_ref.namelist())}")

        self.enable_buttons()
        
    def extract_data(self):
        self.log("Export begun...")

        export_dir = self.export_path.get()

        if not export_dir:
            self.log("Export path is empty.")
            self.enable_buttons()
            return

        # Detect DB automatically
        anki_db = None

        if os.path.exists(os.path.join(export_dir, "collection.anki21")):
            anki_db = os.path.join(export_dir, "collection.anki21")
        elif os.path.exists(os.path.join(export_dir, "collection.anki2")):
            anki_db = os.path.join(export_dir, "collection.anki2")
        else:
            self.log("No Anki database found.")
            return

        media_map_file = os.path.join(export_dir, "media")

        if not os.path.exists(media_map_file):
            self.log("Media map file not found.")
            return

        self.log("Loading media map...")

        with open(media_map_file, "r", encoding="utf-8") as f:
            media_map = json.load(f)
            f.close()

        self.log("Reading notes from database...")

        conn = sqlite3.connect(anki_db)
        cur = conn.cursor()
        cur.execute("SELECT flds FROM notes")

        notes = []

        for (flds,) in cur.fetchall():
            fields = flds.split("\x1f")

            q = fields[0] if len(fields) > 0 else ""
            a = fields[1] if len(fields) > 1 else ""

            all_images = []
            for field in fields:
                matches = re.findall(r'src="([^"]+)"', field)
                all_images.extend(matches)

            notes.append((q, a, all_images))

        conn.close()

        self.log(f"Loaded {len(notes)} notes.")
        self.log("Generating HTML...")

        html = """
        <html>
        <head>
        <meta charset="utf-8">
        <style>
        body { font-family: Arial; padding: 20px; }
        .card { page-break-inside: avoid; margin-bottom: 40px; }
        .question { font-weight: bold; font-size: 14pt; }
        .answer { margin-top: 6px; font-size: 12pt; }
        img { max-width: 400px; margin-top: 10px; }
        hr { border: none; border-top: 1px solid #ccc; margin-top: 20px; }
        </style>
        </head>
        <body>
        """

        for idx, (q, a, img_list) in enumerate(notes, start=1):
            html += f'<div class="card">'
            html += f'<div class="question">Q{idx}: {q}</div>'
            html += f'<div class="answer">A: {a}</div>'

            for img_name in img_list:
                for key, filename in media_map.items():
                    if filename == img_name:
                        real_path = os.path.join(export_dir, key)

                        if os.path.exists(real_path):
                            if self.is_valid_image(real_path):
                                file_url = "file:///" + real_path.replace("\\", "/")
                                html += f'<img src="{file_url}">'
                            else:
                                self.log(f"Skipped invalid image: {real_path}")

            html += "<hr></div>"

            if self.cancel_flag:
                self.log("PDF generation cancelled.")
                return
            
            self.update_progress(idx, len(notes))

        html += "</body></html>"

        ## HTML file saver....
        file_name = "anki_notes_html.html"
        output_html = os.path.join(export_dir, file_name)

        with open(output_html, "w", encoding="utf-8") as f:
            f.write(html)
            f.close()

        self.log(f"HTML file saved: {file_name}")
        ##end here

        output_pdf = os.path.join(export_dir, "anki_notes_pdf.pdf").replace("\\", "/")

        self.log("Generating PDF...")

        config = pdfkit.configuration(
            wkhtmltopdf=r"C:\Program Files\wkhtmltopdf\bin\wkhtmltopdf.exe"
        )

        try:
            pdfkit.from_file(
                output_html,
                output_pdf,
                configuration=config,
                options={"enable-local-file-access": None}
            )

            self.log("PDF generation completed.")
            self.log(f"Saved at: {output_pdf}")

        except Exception as e:
            self.log(f"PDF generation failed: {str(e)}")

        self.enable_buttons()

    def enable_buttons(self):
        self.app.after(0, lambda: self.execute_btn.configure(state="normal"))
        self.app.after(0, lambda: self.extract_btn.configure(state="normal"))
        
    def start_execute_thread(self):
        if self.worker_thread and self.worker_thread.is_alive():
            self.log("Another task is already running.")
            return

        self.cancel_flag = False
        self.execute_btn.configure(state="disabled")
        self.extract_btn.configure(state="disabled")

        self.worker_thread = threading.Thread(target=self.execute, daemon= True)
        self.worker_thread.start()

    def start_extract_thread(self):
        if self.worker_thread and self.worker_thread.is_alive():
            self.log("Another task is already running.")
            return

        self.cancel_flag = False
        self.execute_btn.configure(state="disabled")
        self.extract_btn.configure(state="disabled")

        self.worker_thread = threading.Thread(target=self.extract_data, daemon= True)
        self.worker_thread.start()
        
    def is_valid_image(self, path):
        try:
            with Image.open(path) as img:
                img.verify()
            return True
        except:
            return False

    def on_close(self):
        self.log("Shutting down...")

        self.cancel_flag = True

        if self.worker_thread and self.worker_thread.is_alive():
            self.log("Waiting for worker thread to stop...")
            self.worker_thread.join(timeout=3)

        self.app.destroy()
        
    # ---------------- Run App ----------------

    def run(self):
        self.app.mainloop()


# Start App
if __name__ == "__main__":
    app = AnkiExtractorApp()
    app.run()