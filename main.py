import threading
from threading import Thread
from tkinter import filedialog
import tkinter as tk
import cv2
import time
import os

## OBS! All rotation commands are DISABLED, they currently dont function properly

### ========== GLOBAL* VARS ========== ### 
STATE = {
    "running": False,
    ## Number of current images rendered
    "crt_images": 0,
    ## Store window name of currently selected listbox image
    "listbox_selected_img": '',
}

WINDOWS = {
    ## Store shown images
    # Format: [name, img_MAT, (height, width), always_on_top]
    "shown_img": [],
    ## Store shown videos (data type is different from images)
    # Format: [nname, vid_capture_var, flip] 
    "shown_vids": [],
}

CONFIG = {
    ## Keycode of the key designated to close the program
    "escape_key": 27,
    ## Controls how often certain threads check for closed windows
    "keepimg_timesleep": 0.2,
    ## Duration of each frame of video displays 
    "waitkey_delay": 1,
    ## Supported image file formats
    "image_exts": ("*.png", "*.jpg", "*.jpeg", "*.bmp", "*.tiff"),
    ## Supported video file formats
    "video_exts": ("*.gif", "*.mp4", "*.mov", "*.mkv", "*.avi", "*.mxf"),
}

### ========== FUNCTIONS ========== ###
def find_with_index_nested(arr, idx, element):
    """Return index of first nested element where nested[idx] == element, or -1."""
    for i, el in enumerate(arr):
        try:
            if el[idx] == element:
                return i
        except Exception:
            # malformed entry, skip
            continue
    return -1

def remove_from_listbox(name):
    """Remove item by name from the global `listbox` widget if present."""
    try:
        items = listbox.get(0, tk.END)
    except Exception:
        return
    for i, it in enumerate(items):
        if it == name:
            listbox.delete(i)
            return

def display_video_thread(capt, name):
    """Playback loop for a single video (runs in its own thread)."""
    # find its metadata entry (if any)
    capt_arr = None
    for arr in WINDOWS["shown_vids"]:
        if arr[0] == name:
            capt_arr = arr
            break
    # If for some reason no metadata found, create a minimal one so indices exist
    if capt_arr is None:
        capt_arr = [name, capt, None, None]
        WINDOWS["shown_vids"].append(capt_arr)

    while True:
        if not STATE["running"]:
            break

        ret, frame = capt.read()

        if ret:
            cv2.namedWindow(name, cv2.WINDOW_KEEPRATIO)
            if capt_arr[2] is not None:
                frame = cv2.rotate(frame, capt_arr[2])
            if len(capt_arr) > 3 and capt_arr[3] is not None:
                frame = cv2.flip(frame, capt_arr[3])

            cv2.imshow(name, frame)

            try:
                # allow ESC to break
                if cv2.waitKey(CONFIG["waitkey_delay"]) == CONFIG["escape_key"]:
                    break
                # break when window closed manually
                if cv2.getWindowProperty(name, cv2.WND_PROP_VISIBLE) < 1:
                    break
            except Exception:
                # rare race; continue and let the visible check handle it
                pass
        else:
            # loop the video back to start
            capt.set(cv2.CAP_PROP_POS_FRAMES, 0)
    try:
        capt.release()
    except Exception:
        pass
    # ensure the entry is removed (cleanup)
    for v in list(WINDOWS["shown_vids"]):
        if v[0] == name:
            try:
                WINDOWS["shown_vids"].remove(v)
            except ValueError:
                pass
            break

def check_img_arr():
    """Background process: remove closed windows and update selected dimensions."""
    global wd, ht

    while STATE["running"] == True:
        # Remove closed image windows
        for elem in list(WINDOWS["shown_img"]):  # iterate over a copy
            try:
                if cv2.getWindowProperty(elem[0], cv2.WND_PROP_VISIBLE) < 1:
                    remove_from_listbox(elem[0])
                    try:
                        WINDOWS["shown_img"].remove(elem)
                    except ValueError:
                        pass
                    STATE["crt_images"] = max(0, STATE["crt_images"] - 1)
            except Exception:
                # if getWindowProperty throws, skip this element
                continue
        
        # Remove closed video windows
        for elem in list(WINDOWS["shown_vids"]):
            try:
                if cv2.getWindowProperty(elem[0], cv2.WND_PROP_VISIBLE) < 1:
                    remove_from_listbox(elem[0])
                    try:
                        WINDOWS["shown_vids"].remove(elem)
                    except ValueError:
                        pass
            except Exception:
                # if getWindowProperty throws, skip this element
                continue

        # Autofill width & height when listbox selection changes
        try:
            sel = listbox.curselection()
            if sel and listbox.get(sel) != STATE["listbox_selected_img"]:
                STATE["listbox_selected_img"] = listbox.get(sel)

                idx = find_with_index_nested(
                    WINDOWS["shown_img"],
                    0,
                    STATE["listbox_selected_img"]
                )
                if idx != -1:
                    selected_wnd = WINDOWS["shown_img"][idx]
                    wd.config(textvariable = tk.StringVar(value = selected_wnd[1].shape[:2][1]))
                    ht.config(textvariable = tk.StringVar(value = selected_wnd[1].shape[:2][0]))
                else:
                    # selected item might be a video or removed; clear fields
                    wd.config(textvariable = tk.StringVar(value = ''))
                    ht.config(textvariable = tk.StringVar(value = ''))
        except Exception as e:
            # startup race or listbox not yet present; ignore
            print(f'Encountered exception when accessing listbox: {e}')
            pass

        time.sleep(CONFIG["keepimg_timesleep"])

def keep_images():
    """Background thread that shows images added to WINDOWS['shown_img']."""
    while STATE["running"] == True:
        # If a new image was appended, display it
        if len(WINDOWS["shown_img"]) != STATE["crt_images"]:
            STATE["crt_images"] = len(WINDOWS["shown_img"])
            if STATE["crt_images"] > 0:
                last_img = WINDOWS["shown_img"][-1]
                try:
                    cv2.namedWindow(last_img[0], cv2.WINDOW_KEEPRATIO)
                    cv2.imshow(last_img[0], last_img[1])
                except Exception:
                    # invalid image; remove it
                    try:
                        WINDOWS["shown_img"].remove(last_img)
                        STATE["crt_images"] = len(WINDOWS["shown_img"])
                    except Exception:
                        pass

        # allow ESC to destroy all windows
        if cv2.waitKey(5) == CONFIG["escape_key"]:
            cv2.destroyAllWindows()
        time.sleep(0.01)  # small sleep to avoid tight loop

def resizeImg():
    """Attempts to resize currently selected image"""
    global window, listbox, wd, ht

    try:
        new_wd, new_ht = int(wd.get()), int(ht.get())
        wnd_name = STATE["listbox_selected_img"]
        if wnd_name:
            cv2.resizeWindow(wnd_name, new_wd, new_ht)
        else:
            display_error("No window selected to resize.")
    except Exception as e:
        display_error(f"There was an error when trying to resize image: \n{e}")

def switch_alw_top():
    """Toggles `cv2.WND_PROP_TOPMOST` property"""
    global alw_top_var

    new_val = True if alw_top_var.get() else False
    alw_top_var.set(new_val)

    if STATE["listbox_selected_img"]:
        try:
            cv2.setWindowProperty(STATE["listbox_selected_img"], cv2.WND_PROP_TOPMOST, 1.0 if new_val else 0)
        except Exception as e:
            display_error(f"Could not change topmost property: {e}")

### =================== TKINTER STUFF =================== ###
def openImage():
    """Opens user-selected file. If it is a video, it spawns a separate thread for it"""
    filepath = filedialog.askopenfilename(filetypes = (
        ("All files", "*.*"),
        ("Images", CONFIG["image_exts"]),
        ("Videos", CONFIG["video_exts"])
    ))

    if not filepath:
        return  # user cancelled

    filename = os.path.basename(filepath)
    extension = '*.' + filepath.split('.')[-1].lower()

    # validate extension
    if extension not in CONFIG["image_exts"] + CONFIG["video_exts"]:
        display_error(f'Invalid file type of extension {extension}. Only images and videos are supported!')
        return
    
    # IMAGE
    if extension in CONFIG["image_exts"]:
        # Check if already loaded
        for img in WINDOWS["shown_img"]:
            if filename == img[0]:
                display_error('File is already shown!', 'blue')
                return

        try:
            img = cv2.imread(filepath, cv2.IMREAD_ANYCOLOR)
            if img is None:
                raise ValueError("cv2.imread returned None")
            WINDOWS["shown_img"].append([filename, img, img.shape[:2], False])
            listbox.insert(len(WINDOWS["shown_img"]) - 1, filename)
        except Exception as e:
            display_error(f"Raised error {type(e).__name__}: Please upload a valid image!")
    
    # VIDEO
    elif extension in CONFIG["video_exts"]:
        for vid in WINDOWS["shown_vids"]:
            if filename == vid[0]:
                display_error('File is already shown!', 'blue')
                return

        try:
            capture = cv2.VideoCapture(filepath)
            capture.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            WINDOWS["shown_vids"].append([filename, capture, None, None])
            listbox.insert(0, filename)

            # spawn playback thread for this video
            t = Thread(target = display_video_thread, args = (capture, filename))
            t.daemon = True
            t.start()
        except Exception as e:
            display_error(f"Raised error {type(e).__name__}: Please upload a valid video!")

def display_error(err_txt = '-', text_color = 'red') -> None:
    """Displays error message on the GUI"""  
    try:
        err_msg.config(
            text = '' if err_txt == '-' else err_txt,
            fg = text_color
        )
    except Exception:
        # if GUI not yet built, just print
        print(err_txt)

def get_file_by_name(filename):
    """Returns file by name"""
    for img in WINDOWS["shown_img"]:
        if filename == img[0]:
            return img
    for vid in WINDOWS["shown_vids"]:
        if filename == vid[0]:
            return vid
    return None

def flip_media(FLIPCODE) -> None:
    file_mat_arr = get_file_by_name(STATE["listbox_selected_img"])
    if file_mat_arr is None:
        display_error("No file selected to flip.")
        return

    # VIDEO
    if '*.' + file_mat_arr[0].split('.')[-1].lower() in CONFIG["video_exts"]:
        for vids in WINDOWS["shown_vids"]:
            if vids[0] == file_mat_arr[0]:
                vids[3] = None if vids[3] == FLIPCODE else FLIPCODE
                break
        return

    # IMAGE
    try:
        file_mat_arr[1] = cv2.flip(file_mat_arr[1], FLIPCODE)
        cv2.imshow(file_mat_arr[0], file_mat_arr[1])
    except Exception as e:
        display_error(f"There was an error when trying to flip image: \n{e}")

def rotate_media(direction) -> None:
    """
    Rotates the currently selected image or video by 90 degrees clockwise or counterclockwise.
    direction: `cv2.ROTATE_90_CLOCKWISE` or `cv2.ROTATE_90_COUNTERCLOCKWISE`
    """
    global STATE, WINDOWS

    file_mat_arr = get_file_by_name(STATE["listbox_selected_img"])
    if not file_mat_arr:
        display_error("No image/video selected!")
        return

    # VIDEO
    if '*.' + file_mat_arr[0].split('.')[-1] in CONFIG["video_exts"]:
        for vids in WINDOWS["shown_vids"]:
            if vids[0] == file_mat_arr[0]:
                # Toggle rotation: if same direction -> reset
                if vids[2] == direction:
                    vids[2] = None
                else:
                    vids[2] = direction
                break
        return
    # IMAGE
    display_error(f"Images are not yet supported")
    # # IMAGE
    # if '*.' + file_mat_arr[0].split('.')[-1] in CONFIG["image_exts"]:
    #     for imgs in WINDOWS["shown_img"]:
    #         if imgs[0] == file_mat_arr[0]:
    #             # Toggle rotation: if same direction -> reset
    #             if imgs[2] == direction:
    #                 imgs[2] = None
    #             else:
    #                 imgs[2] = direction
    #             break

    # try:
    #     rotated = cv2.rotate(file_mat_arr[1], direction)
    #     file_mat_arr[1] = rotated
    #     file_mat_arr[2] = rotated.shape[:2]

    #     # schedule the imshow to happen in the GUI thread
    #     window.after(0, lambda: cv2.imshow(file_mat_arr[0], rotated))
    # except Exception as e:
    #     display_error(f"Error rotating image:\n{e}")

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
        command = switch_alw_top,
    )

    fliph_btn = tk.Button(text = "Flip Horizontal", command = lambda: flip_img(1)) # Flip code is 1
    flipv_btn = tk.Button(text = "Flip Vertical", command = lambda: flip_img(0)) # Flip code is 0
    
    rotate_clkwise = tk.Button(
        text = "Rotate Clockwise", 
        command = lambda: rotate_media(cv2.ROTATE_90_CLOCKWISE),
    )
    rotate_cntr_clkwise = tk.Button(
        text = "Rotate Counterclockwise", 
        command = lambda: rotate_media(cv2.ROTATE_90_COUNTERCLOCKWISE),
    )

    # layout
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

    rotate_clkwise.grid(row = 7, column = 0)
    rotate_cntr_clkwise.grid(row = 7, column = 2)

    err_msg.grid(row = 8, columnspan = 3, pady = 15, sticky = tk.S)

    window.mainloop()

### =================== RUNNING MAIN PART =================== ###
if __name__ == "__main__":
    STATE["running"] = True

    th1 = Thread(target = check_img_arr, daemon = True) # check for closed images
    th1.start()

    th2 = Thread(target = keep_images, daemon = True) # keep images shown
    th2.start()

    keep_window_alive() ## Tkinter mainloop
    STATE["running"] = False