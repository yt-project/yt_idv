def add_popup_help(imgui, message: str):
    # adds a hover-triggered popup message to the last-defined imgui item
    if imgui.is_item_hovered():
        imgui.begin_tooltip()
        imgui.text(message)
        imgui.end_tooltip()
