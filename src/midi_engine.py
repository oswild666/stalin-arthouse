import threading
import time
import mido
from typing import Dict

from src.data_models import AppState, Channel, Note, NoteName, Step, TransportState

NOTE_NAMES = [n.value for n in NoteName]

def note_to_midi_int(note: Note) -> int:
    """Converts a Note object to a MIDI integer (0-127)."""
    try:
        note_index = NOTE_NAMES.index(note.name.value)
    except ValueError:
        note_index = 0 # Default to C
    # C4 is MIDI note 60. Formula: 12 * octave + note_index.
    # Our convention seems to be C4 = middle C, so we might need to adjust octave.
    # MIDI standard: C4 = 60.
    # Scientific pitch notation: C4 = middle C.
    # Let's assume octave 4 is the 4th octave, so C4 = 60.
    # C0 = 12, C1 = 24, ..., C4 = 60. Formula: 12 * (octave) + 12 + note_index
    # Let's try a simpler formula that is commonly used:
    midi_val = 12 * (note.octave + 1) + note_index
    return min(127, max(0, midi_val))


NOTE_ON = 0x90
NOTE_OFF = 0x80
PPQN = 24  # Pulses Per Quarter Note

class MidiEngine(threading.Thread):
    def __init__(self, app_state: AppState):
        super().__init__()
        self.app_state = app_state
        self.daemon = True
        self._running = True
        self.ports: Dict[str, mido.ports.BaseOutput] = {}
        self.last_played_note_midi: Dict[int, int] = {} # Keyed by channel.id, value is MIDI note number

    def stop(self):
        """Signals the thread to stop, sends note-offs, and closes ports."""
        self._running = False
        # Send note off for all playing notes
        for channel_id, note_num in self.last_played_note_midi.items():
            channel = next((c for c in self.app_state.project.channels if c.id == channel_id), None)
            if channel and channel.out_port_name in self.ports:
                port = self.ports[channel.out_port_name]
                port.send(mido.Message('note_off', note=note_num, channel=channel_id - 1))

        for port in self.ports.values():
            port.reset() # Sends all-notes-off and resets controllers
            port.close()
        self.ports.clear()

    def get_port(self, port_name: str) -> mido.ports.BaseOutput | None:
        """Opens and returns a MIDI port, caching it for reuse."""
        if port_name not in self.ports:
            try:
                port = mido.open_output(port_name, virtual=True)
                self.ports[port_name] = port
            except (IOError, mido.MidoError):
                return None
        return self.ports.get(port_name)

    def run(self):
        """The main loop of the MIDI engine thread."""
        while self._running:
            project = self.app_state.project

            if project.transport_state != TransportState.PLAYING:
                time.sleep(0.01)
                continue

            pulse_duration = 60.0 / project.bpm / PPQN

            for channel in project.channels:
                if channel.mute or not channel.out_port_name:
                    continue

                pulses_per_step = (PPQN * 4) / channel.division

                if project.playhead_global_step % pulses_per_step == 0:
                    pattern_step_index = int((project.playhead_global_step / pulses_per_step) % channel.pattern_len)

                    step_to_play = channel.steps[pattern_step_index]
                    port = self.get_port(channel.out_port_name)
                    if not port:
                        continue

                    # Send Note Off for the last note played on this channel
                    if channel.id in self.last_played_note_midi:
                        port.send(mido.Message('note_off', note=self.last_played_note_midi[channel.id], channel=channel.id - 1))
                        self.last_played_note_midi.pop(channel.id)

                    # Send Note On for the new note, if any
                    if step_to_play.note:
                        midi_note_number = note_to_midi_int(step_to_play.note)
                        port.send(mido.Message('note_on', note=midi_note_number, velocity=step_to_play.velocity, channel=channel.id - 1))
                        self.last_played_note_midi[channel.id] = midi_note_number

            project.playhead_global_step += 1
            time.sleep(pulse_duration)
