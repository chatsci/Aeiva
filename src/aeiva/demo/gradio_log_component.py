"""Log component of Gradio."""

from __future__ import annotations

import time
from typing import Any, Literal, Optional

import gradio as gr
from gradio.components.base import FormComponent
from gradio.events import Events
from gradio_client.documentation import document

FontWeight = Literal[
    "normal",
    "bold",
    "100",
    "200",
    "300",
    "400",
    "500",
    "600",
    "700",
    "800",
    "900",
]

LogLevel = Literal["trace", "debug", "info", "warn", "error", "off"]


@document()
class Log(FormComponent):
    """
    Create a log component which can continuously read from a log file and display the content in a container.
    """

    EVENTS = [Events.load]

    def find_start_position(self) -> int:
        with open(self.log_file, "rb") as f:
            f.seek(0, 2)

            file_size = f.tell()
            lines_found = 0
            block_size = 1024
            blocks = []

            while f.tell() > 0 and lines_found <= self.tail:
                f.seek(max(f.tell() - block_size, 0))
                block = f.read(block_size)
                blocks.append(block)
                lines_found += block.count(b"\n")
                f.seek(-len(block), 1)

            all_read_bytes = b"".join(reversed(blocks))
            lines = all_read_bytes.splitlines()

            if self.tail >= len(lines):
                return 0
            last_lines = b"\n".join(lines[-self.tail :])
            return file_size - len(last_lines) - 1

    def get_current_reading_pos(self, session_hash: str) -> int:
        if session_hash not in self.current_reading_positions:
            self.current_reading_positions[session_hash] = self.find_start_position()
        return self.current_reading_positions[session_hash]

    def read_to_end(self, session_hash: str) -> bytes:
        with open(self.log_file, "rb") as f:
            current_pos = self.get_current_reading_pos(session_hash)
            f.seek(current_pos)
            b = f.read().decode()
            current_pos = f.tell()
            return b

    def __init__(
        self,
        log_file: str = None,
        tail: int = 100,
        dark: bool = False,
        height: str | int | None = 240,
        xterm_allow_proposed_api: Optional[bool] = False,
        xterm_allow_transparency: Optional[bool] = False,
        xterm_alt_click_moves_cursor: Optional[bool] = True,
        xterm_convert_eol: Optional[bool] = False,
        xterm_cursor_blink: Optional[bool] = False,
        xterm_cursor_inactive_style: Literal[
            "outline", "block", "bar", "underline", "none"
        ] = "outline",
        xterm_cursor_style: Literal["block", "underline", "bar"] = "block",
        xterm_cursor_width: Optional[int] = 1,
        xterm_custom_glyphs: Optional[bool] = False,
        xterm_disable_stdin: Optional[bool] = True,
        xterm_document_override: Optional[Any] = None,
        xterm_draw_bold_text_in_bright_colors: Optional[bool] = True,
        xterm_fast_scroll_modifier: Optional[
            Literal["none", "alt", "ctrl", "shift"]
        ] = "alt",
        xterm_fast_scroll_sensitivity: Optional[int] = 1,
        xterm_font_family: Optional[str] = "courier-new, courier, monospace",
        xterm_font_size: Optional[int] = 15,
        xterm_font_weight: Optional[FontWeight] = "normal",
        xterm_font_weight_bold: Optional[FontWeight] = "bold",
        xterm_ignore_bracketed_paste_mode: Optional[bool] = False,
        xterm_letter_spacing: Optional[float] = 0,
        xterm_line_height: Optional[float] = 1.0,
        xterm_log_level: Optional[LogLevel] = "info",
        xterm_mac_option_click_forces_selection: Optional[bool] = False,
        xterm_mac_option_is_meta: Optional[bool] = False,
        xterm_minimum_contrast_ratio: Optional[int] = 1,
        xterm_overview_ruler_width: Optional[int] = 0,
        xterm_rescale_overlapping_glyphs: Optional[bool] = False,
        xterm_screen_reader_mode: Optional[bool] = False,
        xterm_scroll_on_user_input: Optional[bool] = True,
        xterm_scroll_sensitivity: Optional[int] = 1,
        xterm_scrollback: Optional[int] = 1000,
        xterm_smooth_scroll_duration: Optional[int] = 0,
        xterm_tab_stop_width: Optional[int] = 8,
        xterm_windows_mode: Optional[bool] = False,
        *,
        label: str | None = None,
        info: str | None = None,
        every: float = 0.5,
        show_label: bool | None = None,
        container: bool = True,
        scale: int | None = None,
        min_width: int = 160,
        interactive: bool | None = None,
        visible: bool = True,
        elem_id: str | None = None,
        elem_classes: list[str] | str | None = None,
        render: bool = True,
    ):
        """
        For all the xterm options, please refer to the xterm.js documentation:
        https://xtermjs.org/docs/api/terminal/interfaces/iterminaloptions/

        Parameters:
            log_file: the log file path to read from.
            tail: from the end of the file, the number of lines to start read from.
            dark: if True, will render the component in dark mode.
            label: The label for this component. Appears above the component and is also used as the header if there are a table of examples for this component. If None and used in a `gr.Interface`, the label will be the name of the parameter this component is assigned to.
            info: additional component description.
            every: New log pulling interval.
            show_label: if True, will display label.
            container: If True, will place the component in a container - providing some extra padding around the border.
            scale: relative size compared to adjacent Components. For example if Components A and B are in a Row, and A has scale=2, and B has scale=1, A will be twice as wide as B. Should be an integer. scale applies in Rows, and to top-level Components in Blocks where fill_height=True.
            min_width: minimum pixel width, will wrap if not sufficient screen space to satisfy this value. If a certain scale value results in this Component being narrower than min_width, the min_width parameter will be respected first.
            interactive: if True, will be rendered as an editable textbox; if False, editing will be disabled. If not provided, this is inferred based on whether the component is used as an input or output.
            visible: If False, component will be hidden.
            elem_id: An optional string that is assigned as the id of this component in the HTML DOM. Can be used for targeting CSS styles.
            elem_classes: An optional list of strings that are assigned as the classes of this component in the HTML DOM. Can be used for targeting CSS styles.
            render: If False, component will not render be rendered in the Blocks context. Should be used if the intention is to assign event listeners now but render the component later.
        """
        self.log_file = log_file
        self.tail = tail
        self.dark = dark
        self.current_pos = None
        self.height = height
        self.current_reading_positions = {}

        self.xterm_allow_proposed_api = xterm_allow_proposed_api
        self.xterm_allow_transparency = xterm_allow_transparency
        self.xterm_alt_click_moves_cursor = xterm_alt_click_moves_cursor
        self.xterm_convert_eol = xterm_convert_eol
        self.xterm_cursor_blink = xterm_cursor_blink
        self.xterm_cursor_inactive_style = xterm_cursor_inactive_style
        self.xterm_cursor_style = xterm_cursor_style
        self.xterm_cursor_width = xterm_cursor_width
        self.xterm_custom_glyphs = xterm_custom_glyphs
        self.xterm_disable_stdin = xterm_disable_stdin
        self.xterm_document_override = xterm_document_override
        self.xterm_draw_bold_text_in_bright_colors = (
            xterm_draw_bold_text_in_bright_colors
        )
        self.xterm_fast_scroll_modifier = xterm_fast_scroll_modifier
        self.xterm_fast_scroll_sensitivity = xterm_fast_scroll_sensitivity
        self.xterm_font_family = xterm_font_family
        self.xterm_font_size = xterm_font_size
        self.xterm_font_weight = xterm_font_weight
        self.xterm_font_weight_bold = xterm_font_weight_bold
        self.xterm_ignore_bracketed_paste_mode = xterm_ignore_bracketed_paste_mode
        self.xterm_letter_spacing = xterm_letter_spacing
        self.xterm_line_height = xterm_line_height
        self.xterm_log_level = xterm_log_level
        self.xterm_mac_option_click_forces_selection = (
            xterm_mac_option_click_forces_selection
        )
        self.xterm_mac_option_is_meta = xterm_mac_option_is_meta
        self.xterm_minimum_contrast_ratio = xterm_minimum_contrast_ratio
        self.xterm_overview_ruler_width = xterm_overview_ruler_width
        self.xterm_rescale_overlapping_glyphs = xterm_rescale_overlapping_glyphs
        self.xterm_screen_reader_mode = xterm_screen_reader_mode
        self.xterm_scroll_on_user_input = xterm_scroll_on_user_input
        self.xterm_scroll_sensitivity = xterm_scroll_sensitivity
        self.xterm_scrollback = xterm_scrollback
        self.xterm_smooth_scroll_duration = xterm_smooth_scroll_duration
        self.xterm_tab_stop_width = xterm_tab_stop_width
        self.xterm_windows_mode = xterm_windows_mode

        self.state = gr.State(None)

        super().__init__(
            label=label,
            info=info,
            every=every,
            show_label=show_label,
            container=container,
            scale=scale,
            min_width=min_width,
            interactive=interactive,
            visible=visible,
            elem_id=elem_id,
            elem_classes=elem_classes,
            render=render,
            inputs=[self.state],
            value=self.read_to_end,
        )

        self.load(self.handle_load_event, outputs=self.state)

    def handle_load_event(self, request: gr.Request) -> str:
        return request.session_hash

    def handle_unload_event(self, request: gr.Request):
        print("request on unload: ", request)

    def api_info(self) -> dict[str, Any]:
        return {"type": "string"}

    def example_payload(self) -> Any:
        pass

    def example_value(self) -> Any:
        pass