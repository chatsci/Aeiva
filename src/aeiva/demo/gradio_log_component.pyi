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

from gradio.events import Dependency

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
    from typing import Callable, Literal, Sequence, Any, TYPE_CHECKING
    from gradio.blocks import Block
    if TYPE_CHECKING:
        from gradio.components import Timer

    
    def load(self,
        fn: Callable[..., Any] | None = None,
        inputs: Block | Sequence[Block] | set[Block] | None = None,
        outputs: Block | Sequence[Block] | None = None,
        api_name: str | None | Literal[False] = None,
        scroll_to_output: bool = False,
        show_progress: Literal["full", "minimal", "hidden"] = "full",
        queue: bool | None = None,
        batch: bool = False,
        max_batch_size: int = 4,
        preprocess: bool = True,
        postprocess: bool = True,
        cancels: dict[str, Any] | list[dict[str, Any]] | None = None,
        every: Timer | float | None = None,
        trigger_mode: Literal["once", "multiple", "always_last"] | None = None,
        js: str | None = None,
        concurrency_limit: int | None | Literal["default"] = "default",
        concurrency_id: str | None = None,
        show_api: bool = True,
    
        ) -> Dependency:
        """
        Parameters:
            fn: the function to call when this event is triggered. Often a machine learning model's prediction function. Each parameter of the function corresponds to one input component, and the function should return a single value or a tuple of values, with each element in the tuple corresponding to one output component.
            inputs: list of gradio.components to use as inputs. If the function takes no inputs, this should be an empty list.
            outputs: list of gradio.components to use as outputs. If the function returns no outputs, this should be an empty list.
            api_name: defines how the endpoint appears in the API docs. Can be a string, None, or False. If False, the endpoint will not be exposed in the api docs. If set to None, the endpoint will be exposed in the api docs as an unnamed endpoint, although this behavior will be changed in Gradio 4.0. If set to a string, the endpoint will be exposed in the api docs with the given name.
            scroll_to_output: if True, will scroll to output component on completion
            show_progress: how to show the progress animation while event is running: "full" shows a spinner which covers the output component area as well as a runtime display in the upper right corner, "minimal" only shows the runtime display, "hidden" shows no progress animation at all
            queue: if True, will place the request on the queue, if the queue has been enabled. If False, will not put this event on the queue, even if the queue has been enabled. If None, will use the queue setting of the gradio app.
            batch: if True, then the function should process a batch of inputs, meaning that it should accept a list of input values for each parameter. The lists should be of equal length (and be up to length `max_batch_size`). The function is then *required* to return a tuple of lists (even if there is only 1 output component), with each list in the tuple corresponding to one output component.
            max_batch_size: maximum number of inputs to batch together if this is called from the queue (only relevant if batch=True)
            preprocess: if False, will not run preprocessing of component data before running 'fn' (e.g. leaving it as a base64 string if this method is called with the `Image` component).
            postprocess: if False, will not run postprocessing of component data before returning 'fn' output to the browser.
            cancels: a list of other events to cancel when this listener is triggered. For example, setting cancels=[click_event] will cancel the click_event, where click_event is the return value of another components .click method. Functions that have not yet run (or generators that are iterating) will be cancelled, but functions that are currently running will be allowed to finish.
            every: continously calls `value` to recalculate it if `value` is a function (has no effect otherwise). Can provide a Timer whose tick resets `value`, or a float that provides the regular interval for the reset Timer.
            trigger_mode: if "once" (default for all events except `.change()`) would not allow any submissions while an event is pending. If set to "multiple", unlimited submissions are allowed while pending, and "always_last" (default for `.change()` and `.key_up()` events) would allow a second submission after the pending event is complete.
            js: optional frontend js method to run before running 'fn'. Input arguments for js method are values of 'inputs' and 'outputs', return should be a list of values for output components.
            concurrency_limit: if set, this is the maximum number of this event that can be running simultaneously. Can be set to None to mean no concurrency_limit (any number of this event can be running simultaneously). Set to "default" to use the default concurrency limit (defined by the `default_concurrency_limit` parameter in `Blocks.queue()`, which itself is 1 by default).
            concurrency_id: if set, this is the id of the concurrency group. Events with the same concurrency_id will be limited by the lowest set concurrency_limit.
            show_api: whether to show this event in the "view API" page of the Gradio app, or in the ".view_api()" method of the Gradio clients. Unlike setting api_name to False, setting show_api to False will still allow downstream apps as well as the Clients to use this event. If fn is None, show_api will automatically be set to False.
        
        """
        ...