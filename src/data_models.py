import dataclasses
from enum import Enum
from typing import List, Optional, Dict

class NoteName(Enum):
    C = "C"
    C_SHARP = "C#"
    D = "D"
    D_SHARP = "D#"
    E = "E"
    F = "F"
    F_SHARP = "F#"
    G = "G"
    G_SHARP = "G#"
    A = "A"
    A_SHARP = "A#"
    B = "B"

class LoopMode(Enum):
    FORWARD = "forward"
    BOUNCE = "bounce"

class TransportState(Enum):
    STOPPED = "stopped"
    PLAYING = "playing"
    PAUSED = "paused"

@dataclasses.dataclass
class Note:
    name: NoteName
    octave: int = 4  # Default to 4th octave

@dataclasses.dataclass
class Step:
    note: Optional[Note] = None
    velocity: int = 100
    gate: float = 0.9  # 90% of step duration

@dataclasses.dataclass
class Channel:
    id: int
    name: str
    out_port_name: Optional[str] = None
    pattern_len: int = 16
    division: int = 16  # e.g., 16 for 1/16th notes
    loop_mode: LoopMode = LoopMode.FORWARD
    mute: bool = False
    randomize: Dict[str, int] = dataclasses.field(default_factory=lambda: {"vel_range": 0, "gate_range": 0})
    steps: List[Step] = dataclasses.field(default_factory=list)

    # UI-related state
    page_index: int = 0
    cursor_step_idx: int = 0
    bounce_dir: int = 1

    def __post_init__(self):
        # Ensure steps list has the correct length
        if not self.steps:
            self.steps = [Step() for _ in range(self.pattern_len)]
        elif len(self.steps) != self.pattern_len:
             # Adjust list size if pattern_len changes
            current_len = len(self.steps)
            if self.pattern_len > current_len:
                self.steps.extend([Step() for _ in range(self.pattern_len - current_len)])
            else:
                self.steps = self.steps[:self.pattern_len]


@dataclasses.dataclass
class Project:
    bpm: int = 120
    channels: List[Channel] = dataclasses.field(default_factory=list)
    transport_state: TransportState = TransportState.STOPPED
    playhead_global_step: int = 0

@dataclasses.dataclass
class AppState:
    """A simple class to hold the application's state."""
    project: Project
    active_channel_idx: int = 0
    running: bool = True

    def get_active_channel(self) -> Optional[Channel]:
        """Returns the currently active channel, if any."""
        if self.project.channels and 0 <= self.active_channel_idx < len(self.project.channels):
            return self.project.channels[self.active_channel_idx]
        return None
