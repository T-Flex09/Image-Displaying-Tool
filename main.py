from threading import Thread
from tkinter import filedialog
import tkinter as tk
import cv2
import time

### ========== GLOBAL* VARS ========== ### 
KEEPIMG_TIMESLEEP = .2

crt_images = 0
running = False

## Store the shown images
# Format: [name, img_MAT, (height, width), always_on_top]
shown_img = []

## Store window name of currently selected listbox image
listbox_selected_img = ''


## Find element by index in nested array
def find_with_index_nested(arr, idx, element):
    index = 0
    for el in arr:
        if el[idx] == element: return index
        index += 1
    
    return -1
### ========== GLOBAL* VARS ========== ###



def check_img_arr():
    global listbox, crt_images, wd, ht, listbox_selected_img
    global on_top_btn, alw_top_var

    while running:
        ## Delete item from listbox if window was closed
        for elem in shown_img:
            if cv2.getWindowProperty(elem[0], cv2.WND_PROP_VISIBLE) < 1: # If window was closed
                listbox_tuple = listbox.get(0, tk.END)

                for item in range(len(listbox_tuple)):
                    if listbox_tuple[item] == elem[0]:
                        listbox.delete(item)
                        break
                
                shown_img.remove(elem)
                crt_images -= 1
        
        ## Autofill width & height in the corresponding fields when item is selected
        try:
            if listbox.curselection() and listbox.get(listbox.curselection()) != listbox_selected_img:
                listbox_selected_img = listbox.get(listbox.curselection())

                selected_wnd = shown_img[find_with_index_nested(
                    shown_img, 
                    0, 
                    listbox_selected_img
                )]
                
                wd.config(textvariable = tk.StringVar(value = selected_wnd[1].shape[:2][1]))
                ht.config(textvariable = tk.StringVar(value = selected_wnd[1].shape[:2][0]))

        except Exception as e:
            # most CERTAINLY a startup error and idk how to fix it 💔, listbox gets referenced before actual initialization
            print(f'Encountered exception stating [{(e)}] when loading `listbox`. Probably a startup error.')

        time.sleep(KEEPIMG_TIMESLEEP)


def keep_images():
    global crt_images

    while running:
        ## Check if image has been added to `shown_img[]`
        if len(shown_img) != crt_images:
            crt_images = len(shown_img)
            
            last_img = shown_img[len(shown_img) - 1]
            cv2.namedWindow(last_img[0], cv2.WINDOW_KEEPRATIO)
            cv2.imshow(last_img[0], last_img[1]) # [name, img array]

            ## Saved for later idk
            # cv2.resizeWindow(last_img[0], last_img[1].shape[1], last_img[1].shape[0])

        
        ## DESTROY ALL
        if cv2.waitKey(5) == 27: # esc 
            cv2.destroyAllWindows()


def resizeImg():
    global window, listbox, wd, ht

    try:
        new_wd, new_ht = int(wd.get()), int(ht.get())
        wnd_name = listbox_selected_img #listbox.get(listbox.curselection())
        
        cv2.resizeWindow(wnd_name, new_wd, new_ht)
    except Exception as e: 
        display_error(f"There was an error when trying to resize image: \n{e}")


def switch_alw_top():
    global alw_top_var
    
    new_val = True if alw_top_var.get() else False
    alw_top_var.set(new_val)
    
    if listbox_selected_img != '':
        cv2.setWindowProperty(listbox_selected_img, cv2.WND_PROP_TOPMOST, 1.0 if new_val else 0)
    

### =================== TKINTER STUFF =================== ###
def openImage():    
    filepath = filedialog.askopenfilename(filetypes = (
        ("Images", ("*.png", "*.jpg", "*.jpeg")),
        ("All files", "*.*")
    ))
    filename = filepath.split('/')[-1]

    ## CHECK IF IMAGE IS ALREADY LOADED
    for img in shown_img:
        if filename == img[0]:
            display_error('File is already shown!', 'blue')
            return 

    try:
        if filepath:
            img = cv2.imread(filepath, cv2.IMREAD_ANYCOLOR)

        shown_img.append([f"{filename}", img, img.shape[:2], False])
        listbox.insert(len(shown_img) - 1, filename)
    except Exception as e:
        display_error(f"Raised error of type {type(e).__name__}. Please upload a valid image!")

def display_error(err_txt = '-', text_color = 'red'):   
    err_msg.config(
        text = '' if err_txt == '-' else err_txt, 
        fg = text_color
    )



def keep_window_alive():
    global window, listbox, wd, ht, err_msg, on_top_btn, alw_top_var

    window = tk.Tk()
    window.title("Active Image Tool")
    window.geometry("300x310")
    # window.resizable(False, False)

    window.grid_columnconfigure(0, weight = 1)
    
    listbox = tk.Listbox(window)
    label = tk.Label(window, text = "Active Windows")
    button = tk.Button(text = "Select File", command = openImage)

    wd_lbl = tk.Label(window, text = "Width: ")
    ht_lbl = tk.Label(window, text = "Height: ")
    wd = tk.Entry(window)
    ht = tk.Entry(window)
    resize_btn = tk.Button(text = "Resize", command = resizeImg)

    err_msg = tk.Label(window, fg = "red", wraplength = 275)

    alw_top_var = tk.BooleanVar()
    on_top_btn = tk.Checkbutton(
        text = "Stays on top?", 
        variable = alw_top_var, 
        command = switch_alw_top
    )


    button.grid(row = 0, column = 0, columnspan = 3)
    label.grid(row = 1, column = 0, columnspan = 3)
    listbox.grid(row = 2, column = 0, columnspan = 3)

    wd_lbl.grid(row = 3, column = 1, sticky = tk.E)
    wd.grid(row = 3, column = 2)
    ht_lbl.grid(row = 4, column = 1, sticky = tk.E)
    ht.grid(row = 4, column = 2)
    resize_btn.grid(row = 3, column = 0, rowspan = 2)
    on_top_btn.grid(row = 5, columnspan = 3)

    err_msg.grid(row = 6, columnspan = 3, pady = 15, sticky = tk.S)

    window.mainloop()


### =================== RUNNING MAIN PART =================== ###
if __name__ == "__main__":
    running = True

    th1 = Thread(target = check_img_arr) # check for closed images
    th1.start()

    th2 = Thread(target = keep_images) # keep images shown
    th2.start()

    keep_window_alive() ## Tkinter mainloop
    running = False