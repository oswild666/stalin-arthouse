import io
import io

from rich.console import Console

from prompt_toolkit.application import Application
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.layout.containers import Window
from prompt_toolkit.layout.controls import FormattedTextControl
from prompt_toolkit.layout.layout import Layout

from src.ui import create_layout, update_layout
from src.data_models import Project, Channel, Step, Note, NoteName, LoopMode, TransportState, AppState
from src.midi_engine import MidiEngine

def main():
    """Main function to run the application."""

    # --- Create a sample project for demonstration ---
    # Start with an empty project to test the 'add channel' feature
    project = Project(bpm=120)
    # ----------------------------------------------------

    app_state = AppState(project=project)
    midi_engine = MidiEngine(app_state)

    # --- Key Bindings ---
    kb = KeyBindings()

    @kb.add('c-c')
    @kb.add('c-q')
    def _(event):
        """Signal the midi engine to stop and then quit the application."""
        midi_engine.stop()
        event.app.exit()

    @kb.add('left')
    def _(event):
        channel = app_state.get_active_channel()
        if channel:
            channel.cursor_step_idx = max(0, channel.cursor_step_idx - 1)
            event.app.invalidate()

    @kb.add('right')
    def _(event):
        channel = app_state.get_active_channel()
        if channel:
            channel.cursor_step_idx = min(channel.pattern_len - 1, channel.cursor_step_idx + 1)
            event.app.invalidate()

    @kb.add('1')
    def _(event):
        if len(app_state.project.channels) >= 1:
            app_state.active_channel_idx = 0
            event.app.invalidate()

    @kb.add('2')
    def _(event):
        if len(app_state.project.channels) >= 2:
            app_state.active_channel_idx = 1
            event.app.invalidate()

    @kb.add('3')
    def _(event):
        if len(app_state.project.channels) >= 3:
            app_state.active_channel_idx = 2
            event.app.invalidate()

    @kb.add('[')
    def _(event):
        channel = app_state.get_active_channel()
        if channel:
            channel.page_index = max(0, channel.page_index - 1)
            event.app.invalidate()

    @kb.add(']')
    def _(event):
        channel = app_state.get_active_channel()
        if channel:
            # Max 4 pages (0, 1, 2, 3) for 64 steps
            max_page = (channel.pattern_len - 1) // 16
            channel.page_index = min(max_page, channel.page_index + 1)
            event.app.invalidate()

    @kb.add('space')
    def _(event):
        if app_state.project.transport_state == TransportState.PLAYING:
            app_state.project.transport_state = TransportState.PAUSED
        else: # Was stopped or paused
            app_state.project.transport_state = TransportState.PLAYING
        event.app.invalidate()

    @kb.add('s')
    def _(event):
        app_state.project.transport_state = TransportState.STOPPED
        app_state.project.playhead_global_step = 0
        event.app.invalidate()

    @kb.add('r')
    def _(event):
        app_state.project.transport_state = TransportState.PLAYING
        app_state.project.playhead_global_step = 0
        event.app.invalidate()

    @kb.add('n')
    def _(event):
        """Add a new channel if there are less than 3."""
        if len(app_state.project.channels) < 3:
            new_id = len(app_state.project.channels) + 1
            new_channel = Channel(
                id=new_id,
                name=f"CH{new_id}",
                out_port_name=f"TrackerPort {new_id}"
            )
            app_state.project.channels.append(new_channel)
            # Set the new channel as active
            app_state.active_channel_idx = len(app_state.project.channels) - 1
            event.app.invalidate()

    # --- UI Rendering Bridge ---
    rich_layout = create_layout()

    def get_content():
        """Render the rich layout to a string and return it."""
        # Create a temporary console that writes to a string buffer
        string_io = io.StringIO()
        console = Console(file=string_io, width=100, height=36, record=True)
        # Update the rich layout with the current state
        update_layout(rich_layout, app_state.project, app_state.active_channel_idx)
        # Print the layout to the console
        console.print(rich_layout)
        # Return the console's output as formatted text for prompt_toolkit
        return console.export_text(styles=True)

    # --- Application Setup ---
    # The control that will display our rich-rendered content
    control = FormattedTextControl(
        text=get_content,
        key_bindings=kb,
        focusable=True,
        show_cursor=False
    )

    # The main prompt_toolkit layout
    pt_layout = Layout(container=Window(content=control))

    app = Application(layout=pt_layout, full_screen=True)

    # --- Run Application ---
    midi_engine.start()
    try:
        app.run()
    finally:
        # Ensure the MIDI engine is stopped gracefully
        midi_engine.stop()
        midi_engine.join(timeout=1)

    print("\n[bold red]Приложение закрыто.[/bold red]")


if __name__ == "__main__":
    main()
