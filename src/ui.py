from rich.layout import Layout
from rich.panel import Panel
from rich.console import Console
from rich.text import Text
from rich.align import Align
from rich.table import Table

# Import data models
from src.data_models import Project, Channel, Step, Note, NoteName, LoopMode

console = Console(width=100, height=36)

def render_channel(channel: Channel, is_active: bool) -> Panel:
    """Renders a single channel into a Rich Panel."""
    border_style = "yellow" if is_active else "blue"

    # Header
    loop_emoji = "→→⭐" if channel.loop_mode == LoopMode.FORWARD else "↔️⭐"
    port_name = channel.out_port_name if channel.out_port_name else "<None>"
    header = f"[bold]{channel.name}[/bold] | 🎺 Out: {port_name} | Div: 1/{channel.division} | Len: {channel.pattern_len} | Loop: {loop_emoji}"

    # Grid
    grid = Table.grid(expand=True)
    grid.add_column("index", justify="center", style="cyan")
    grid.add_column("notes", justify="left")

    steps_per_page = 16
    start_step = channel.page_index * steps_per_page
    end_step = start_step + steps_per_page

    # Note Formatting
    note_line = []
    for i, step in enumerate(channel.steps[start_step:end_step]):
        idx = start_step + i
        note_str = "·"
        if step.note:
            note_str = f"{step.note.name.value}{step.note.octave}"

        # Pad to 3 chars for alignment
        note_str = note_str.ljust(3)

        if idx == channel.cursor_step_idx:
            note_line.append(f"[reverse]{note_str}[/reverse]")
        else:
            note_line.append(note_str)

    # Index line
    index_line = " ".join([f"{i+1:02}" for i in range(start_step, end_step)])

    grid.add_row(Text(index_line, style="bold magenta"))
    grid.add_row(" ".join(note_line))

    return Panel(grid, title=header, border_style=border_style)

def create_layout() -> Layout:
    """Creates the main layout for the application."""
    layout = Layout(name="root")
    layout.split(
        Layout(name="header", size=3),
        Layout(ratio=1, name="main_body"),
        Layout(size=1, name="footer"),
    )
    layout["main_body"].split_row(Layout(name="channels_area"), Layout(name="inspector", size=30))
    layout["header"].split_row(Layout(name="info_panel"), Layout(name="controls_panel"))
    return layout

def update_layout(layout: Layout, project: Project, active_channel_idx: int):
    """Updates the layout with the current project state."""
    # Top Bar
    layout["info_panel"].update(Panel(f"⏱️ BPM: {project.bpm}", title="[bold cyan]Project Info[/bold cyan]", border_style="green"))
    layout["controls_panel"].update(Panel("🚀▶️ Play | 🔁🚩 Restart | ⛔🧨 Stop", title="[bold cyan]Transport[/bold cyan]", border_style="green"))

    # Channels Area
    channels_layout = Layout(name="channels_stack")
    channel_panels = [render_channel(ch, i == active_channel_idx) for i, ch in enumerate(project.channels)]

    if channel_panels:
        channels_layout.split_column(*channel_panels)
    else:
        channels_layout.update(
            Align.center("[italic cyan]No channels yet.\nPress 'n' to add one![/italic cyan]", vertical="middle")
        )

    add_channel_text = f"➕🚩 Добавить канал (осталось: {3 - len(project.channels)})"
    if len(project.channels) >= 3:
        add_channel_text = "[dim]Больше каналов добавить нельзя[/dim]"

    add_channel_panel = Panel(
        Align.center(add_channel_text),
        border_style="dashed green"
    )

    # Create a new layout for the channels area and split it correctly
    channels_area_layout = Layout()
    channels_area_layout.split_column(
        channels_layout,
        Layout(add_channel_panel, size=3) # Give the button a fixed size of 3 lines
    )
    layout["channels_area"].update(channels_area_layout)

    # Inspector Placeholder
    inspector_placeholder = "[italic gray50]Детали выбранного шага..."
    if project.channels:
        active_channel = project.channels[active_channel_idx]
        step = active_channel.steps[active_channel.cursor_step_idx]
        note_display = "--"
        if step.note:
            note_display = f"{step.note.name.value}{step.note.octave}"

        inspector_placeholder = (
            f"Канал: {active_channel.name}\n"
            f"Шаг: {active_channel.cursor_step_idx + 1}\n"
            f"Нота: {note_display}\n"
            f"Velo: {step.velocity}\n"
            f"Gate: {step.gate*100:.0f}%\n"
        )

    layout["inspector"].update(Panel(inspector_placeholder, title="[bold cyan]Inspector[/bold cyan]", border_style="magenta"))

    # Footer Placeholder
    page_char = chr(ord('A') + (project.channels[active_channel_idx].page_index if project.channels else 0))
    start_step = (project.channels[active_channel_idx].page_index * 16) + 1 if project.channels else 1
    end_step = start_step + 15
    footer_text = f"[bold]Стр: {page_char} ({start_step}–{end_step}) | [ и ] - страницы | 1/2/3 - фокус канала | Стрелки - навигация[/bold]"
    layout["footer"].update(Panel(footer_text, border_style="yellow"))


if __name__ == "__main__":
    from rich.live import Live
    import time
    from src.data_models import Channel, Step, Note, NoteName

    # Create a sample project for demonstration
    project = Project(bpm=128)
    ch1 = Channel(id=1, name="CH1", pattern_len=32)
    ch1.steps[0] = Step(note=Note(name=NoteName.C, octave=4))
    ch1.steps[2] = Step(note=Note(name=NoteName.E, octave=4))
    ch1.steps[4] = Step(note=Note(name=NoteName.G, octave=4))
    ch1.steps[8] = Step(note=Note(name=NoteName.C, octave=5))
    ch1.cursor_step_idx = 4 # put cursor on the G4 note

    ch2 = Channel(id=2, name="CH2", out_port_name="Virtual MIDI 2", division=8, loop_mode=LoopMode.BOUNCE)
    ch2.steps[1] = Step(note=Note(name=NoteName.A_SHARP, octave=2))
    ch2.steps[3] = Step(note=Note(name=NoteName.A_SHARP, octave=2))

    project.channels.extend([ch1, ch2])

    layout = create_layout()

    with Live(layout, screen=True, redirect_stderr=False) as live:
        try:
            update_layout(layout, project, active_channel_idx=0)
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            pass
