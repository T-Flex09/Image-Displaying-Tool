import threading
from threading import Thread
from tkinter import filedialog
import tkinter as tk
import cv2
import time

## OBS! All rotation commands are DISABLED, they currently dont function properly



### ========== GLOBAL* VARS ========== ### 
KEEPIMG_TIMESLEEP = .2

waitkey_delay = 1 #int((1 / 30) * 1000) ## Duration of each frame of video displays

crt_images = 0
running = False

image_extension_tuple = ("*.png", "*.jpg", "*.jpeg")
video_extension_tuple = ("*.gif,", "*.mp4", "*.mov", "*.mkv")

## Store shown images
# Format: [name, img_MAT, (height, width), always_on_top]
shown_img = []

## Store shown videos (data type is different from images)
# Format: [nname, vid_capture_var, flip] 
shown_vids = []

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



def display_video_thread(capt, name):
    capt_arr = []
    for arr in shown_vids:
        if arr[0] == name: 
            capt_arr = arr
            break
    
    while True:
        ret, frame = capt.read()

        if ret:
            cv2.namedWindow(name, cv2.WINDOW_KEEPRATIO)
            # if capt_arr[2] != None: frame = cv2.rotate(frame, capt_arr[2])
            if capt_arr[3] != None: 
                frame = cv2.flip(frame, capt_arr[3])

            cv2.imshow(name, frame)

            try:
                if cv2.waitKey(waitkey_delay) == 27:
                    break
                if cv2.getWindowProperty(name, cv2.WND_PROP_VISIBLE) < 1:
                    break

            except Exception as e:
                print(e)
        else:
            capt.set(cv2.CAP_PROP_POS_FRAMES, 0)
    
    capt.release()


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
        
        for elem in shown_vids:
            if cv2.getWindowProperty(elem[0], cv2.WND_PROP_VISIBLE) < 1:
                listbox_tuple = listbox.get(0, tk.END)

                for item in range(len(listbox_tuple)):
                    if listbox_tuple[item] == elem[0]:
                        listbox.delete(item)
                        break
                
                shown_vids.remove(elem)

        
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
        ("All files", "*.*"),
        ("Images", image_extension_tuple),
        ("Videos", video_extension_tuple)
    ))
    filename = filepath.split('/')[-1]
    extension = '*.' + filepath.split('.')[-1]

    if extension not in image_extension_tuple + video_extension_tuple:
        display_error(f'Invalid file type of extension {extension}. Only images and videos are currently supported!')
        return
    
    ## Check if file is image
    if extension in image_extension_tuple:
        ## CHECK IF FILE IS ALREADY LOADED
        for img in shown_img:
            if filename == img[0]:
                display_error('File is already shown!', 'blue')
                return 

        try:
            if filepath:
                img = cv2.imread(filepath, cv2.IMREAD_ANYCOLOR)

            shown_img.append([filename, img, img.shape[:2], False])
            listbox.insert(len(shown_img) - 1, filename)
        except Exception as e:
            display_error(f"Raised error of type {type(e).__name__}. Please upload a valid image!")
    
    ## Check if file is video
    if extension in video_extension_tuple:
        for vid in shown_vids:
            if filename == vid[0]:
                display_error('File is already shown!', 'blue')
                return             

        try:
            if filepath:
                capture = cv2.VideoCapture(filepath)
                capture.set(cv2.CAP_PROP_BUFFERSIZE, 1)

            shown_vids.append([filename, capture, None, None])
            listbox.insert(0, filename)

            # Enable separate thread for video display
            t = Thread(target = display_video_thread, args = (capture, filename))
            t.daemon = True
            t.start()

        except Exception as e:
            display_error(f"Raised error of type {type(e).__name__}. Please upload a valid video!")


def display_error(err_txt = '-', text_color = 'red') -> None:   
    err_msg.config(
        text = '' if err_txt == '-' else err_txt, 
        fg = text_color
    )

def get_file_by_name(filename):
    for img in shown_img:
        if filename == img[0]: return img
    for vid in shown_vids:
        if filename == vid[0]: return vid
    return None


def flip_img(FLIPCODE) -> None:
    global window, listbox
    
    file_mat_arr = get_file_by_name(listbox_selected_img)

    ## Handle video file case
    if '*.' + file_mat_arr[0].split('.')[-1] in video_extension_tuple:
        for vids in shown_vids:
            if vids[0] == file_mat_arr[0]:
                if vids[3] == FLIPCODE: vids[3] = None
                else: 
                    vids[3] = FLIPCODE
                
                break
        return

    try: 
        file_mat_arr[1] = cv2.flip(file_mat_arr[1], FLIPCODE)
        cv2.imshow(file_mat_arr[0], file_mat_arr[1])
    except Exception as e:
        display_error(f"There was an error when trying to flip image: \n{e}")


# def rotate_img(direction) -> None:
#     global window, listbox

#     file_mat_arr = get_file_by_name(listbox_selected_img)

#     try: 
#         file_mat_arr[1] = cv2.rotate(file_mat_arr[1], direction)
#         cv2.imshow(file_mat_arr[0], file_mat_arr[1])
#     except Exception as e:
#         display_error(f"There was an error when trying to rotate image: \n{e}")



def keep_window_alive():
    global window, listbox, wd, ht, err_msg, on_top_btn, alw_top_var

    window = tk.Tk()
    window.title("Active Image Tool")
    window.geometry("300x375")
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

    fliph_btn = tk.Button(text = "Flip Horizontal", command = lambda: flip_img(1)) # Flip code is 1
    flipv_btn = tk.Button(text = "Flip Vertical", command = lambda: flip_img(0)) # Flip code is 0
    # rotate_clkwise = tk.Button(text = "Rotate Clockwise", command = lambda: rotate_img(cv2.ROTATE_90_CLOCKWISE))
    # rotate_cntr_clkwise = tk.Button(text = "Rotate Counterclockwise", command = lambda: rotate_img(cv2.ROTATE_90_COUNTERCLOCKWISE))
    
    ## Rotation doesnt really work on non-square images !!!!


    button.grid(row = 0, column = 0, columnspan = 3)
    label.grid(row = 1, column = 0, columnspan = 3)
    listbox.grid(row = 2, column = 0, columnspan = 3)

    wd_lbl.grid(row = 3, column = 1, sticky = tk.E)
    wd.grid(row = 3, column = 2)
    ht_lbl.grid(row = 4, column = 1, sticky = tk.E)
    ht.grid(row = 4, column = 2)
    resize_btn.grid(row = 3, column = 0, rowspan = 2)
    on_top_btn.grid(row = 6, columnspan = 3)

    fliph_btn.grid(row = 5, column = 0)
    flipv_btn.grid(row = 5, column = 2)
    # rotate_clkwise.grid(row = 7, column = 0)
    # rotate_cntr_clkwise.grid(row = 7, column = 1)

    err_msg.grid(row = 8, columnspan = 3, pady = 15, sticky = tk.S)

    window.mainloop()


### =================== RUNNING MAIN PART =================== ###
if __name__ == "__main__":
    running = True

    th1 = Thread(target = check_img_arr, daemon = True) # check for closed images
    th1.start()

    th2 = Thread(target = keep_images, daemon = True) # keep images shown
    th2.start()

    keep_window_alive() ## Tkinter mainloop
    running = False