import os
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import threading

# Libraritë për konvertim
from pdf2docx import Converter
import pdfplumber
import openpyxl


def konverto_ne_word(pdf_path, docx_path):
    cv = Converter(pdf_path)
    cv.convert(docx_path, start=0, end=None)
    cv.close()


def konverto_ne_excel(pdf_path, excel_path):
    wb = openpyxl.Workbook()
    # Heqim faqen e parë të zbrazët që krijohet automatikisht
    wb.remove(wb.active)

    with pdfplumber.open(pdf_path) as pdf:
        for i, page in enumerate(pdf.pages):
            # Krijojmë një fletë (Sheet) të re në Excel për çdo faqe të PDF-së
            ws = wb.create_sheet(title=f"Faqja {i+1}")
            tables = page.extract_tables()

            for table in tables:
                for row in table:
                    # Pastrojmë vlerat None që mund të vijnë nga qelizat e zbrazëta
                    cleaned_row = ["" if cell is None else str(cell) for cell in row]
                    ws.append(cleaned_row)

            # Nëse faqja nuk ka tabela, nxjerrim tekstin e thjeshtë rresht pas rreshti
            if not tables:
                text = page.extract_text()
                if text:
                    for line in text.split("\n"):
                        ws.append([line])

    wb.save(excel_path)


def procesi_konvertimit(folder_path, progress_bar, status_label, btn_start, formati):
    if not folder_path:
        messagebox.showwarning("Kujdes", "Ju lutem zgjidhni një folder më parë!")
        btn_start.config(state=tk.NORMAL)
        return

    skedaret = [f for f in os.listdir(folder_path) if f.lower().endswith(".pdf")]

    if not skedaret:
        messagebox.showinfo("Njoftim", "Nuk u gjet asnjë skedar PDF në këtë folder.")
        btn_start.config(state=tk.NORMAL)
        return

    total = len(skedaret)
    progress_bar["maximum"] = total
    konvertuar = 0

    for i, skedar in enumerate(skedaret):
        pdf_path = os.path.join(folder_path, skedar)
        emri_pa_prapashtese = os.path.splitext(skedar)[0]

        status_label.config(text=f"Duke konvertuar ({i+1}/{total}): {skedar}")
        root.update_idletasks()

        try:
            if formati == "Word":
                docx_path = os.path.join(folder_path, f"{emri_pa_prapashtese}.docx")
                konverto_ne_word(pdf_path, docx_path)
            elif formati == "Excel":
                excel_path = os.path.join(folder_path, f"{emri_pa_prapashtese}.xlsx")
                konverto_ne_excel(pdf_path, excel_path)

            konvertuar += 1
        except Exception as e:
            print(f"Gabim te {skedar}: {e}")

        progress_bar["value"] = i + 1
        root.update_idletasks()

    status_label.config(text="Procesi përfundoi!")
    messagebox.showinfo(
        "Sukses",
        f"U konvertuan me sukses {konvertuar} nga {total} skedarë në formatin {formati}!",
    )
    progress_bar["value"] = 0
    btn_start.config(state=tk.NORMAL)


def nis_konvertimin_thread():
    btn_start.config(state=tk.DISABLED)
    formati_zgjedhur = format_var.get()
    threading.Thread(
        target=procesi_konvertimit,
        args=(Folder_path.get(), progress, lbl_status, btn_start, formati_zgjedhur),
        daemon=True,
    ).start()


def zgjidh_folderin():
    folder_selected = filedialog.askdirectory()
    if folder_selected:
        Folder_path.set(folder_selected)
        lbl_folder.config(text=f"Folderi i zgjedhur: {folder_selected}")


# Krijimi i dritares kryesore
root = tk.Tk()
root.title("Konvertuesi PDF -> Word+Excel -- A.XHAFA'26")
root.geometry("500x320")
root.resizable(False, False)

Folder_path = tk.StringVar()
format_var = tk.StringVar(value="Word")  # Vlera fillestar është Word

# UI Elements
lbl_instruction = tk.Label(
    root,
    text="1. Krijo një folder të ri për të futur fajlat PDF,\n ku dhe do të ruhen fajlat e konvertuar.",
    font=("Arial", 10, "bold"),
)
lbl_instruction.pack(pady=10)

btn_browse = tk.Button(
    root,
    text="Zgjidh Folderin",
    command=zgjidh_folderin,
    bg="#2196F3",
    fg="white",
    font=("Arial", 10),
)
btn_browse.pack(pady=5)

lbl_folder = tk.Label(
    root, text="Nuk është zgjedhur asnjë folder.", fg="gray", wraplength=450
)
lbl_folder.pack(pady=5)

# Pjesa e zgjedhjes së Formatit
lbl_format = tk.Label(
    root, text="2. Zgjidhni formatin e daljes:", font=("Arial", 10, "bold")
)
lbl_format.pack(pady=5)

frame_radio = tk.Frame(root)
frame_radio.pack()
rb_word = tk.Radiobutton(
    frame_radio,
    text="Word (.docx)",
    variable=format_var,
    value="Word",
    font=("Arial", 10),
)
rb_word.pack(side=tk.LEFT, padx=15)
rb_excel = tk.Radiobutton(
    frame_radio,
    text="Excel (.xlsx)",
    variable=format_var,
    value="Excel",
    font=("Arial", 10),
)
rb_excel.pack(side=tk.LEFT, padx=15)

# Butoni i nisjes dhe progresi
btn_start = tk.Button(
    root,
    text="Nis Konvertimin",
    command=nis_konvertimin_thread,
    bg="#4CAF50",
    fg="white",
    font=("Arial", 11, "bold"),
)
btn_start.pack(pady=15)

progress = ttk.Progressbar(root, orient="horizontal", length=400, mode="determinate")
progress.pack(pady=5)

lbl_status = tk.Label(root, text="", fg="blue")
lbl_status.pack(pady=5)

root.mainloop()
