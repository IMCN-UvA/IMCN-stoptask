from exptools.core.session import MRISession
from StopStimulus import StopStimulus, FixationCircle
from StopTrial import StopSignalTrial
from psychopy import visual, data
import pandas as pd
import numpy as np
import os
import pyaudio
import subprocess
import wave
from scipy.io import wavfile
import copy


class StopSignalSession(MRISession):

    def __init__(self, subject_initials, index_number, run, tr, config):
        super(StopSignalSession, self).__init__(subject_initials,
                                                index_number,
                                                tr=tr,
                                                simulate_mri_trigger=False,
                                                # NB: DO NOT use this MRI simulation option, but rather another!
                                                mri_trigger_key=config.get('mri', 'mri_trigger_key'))

        self.config = config
        self.run_nr = run

        if config.get('audio', 'engine') == 'psychopy':
            # BEFORE moving on, ensure that the correct audio driver is selected
            from psychopy import prefs
            prefs.general['audioLib'] = config.get('audio', 'backend')
            from psychopy.sound import Sound

            self.bleeper = Sound(secs=0.5,
                                 octave=4,
                                 loops=0,
                                 sampleRate=44100,  name='')
            self.bleeper.play()

        elif config.get('audio', 'engine') == 'TK':
            self.setup_sound_system()
            self.read_sound_file('sounds/0.wav', '0')

            # to test sound:
            self.play_sound(sound_index=0)

        self.response_button_signs = [config.get('input', 'response_button_left'),
                                      config.get('input', 'response_button_right')]

        screen = self.create_screen(engine='psychopy',
                                    size=config.get('screen', 'size'),
                                    full_screen=config.get('screen', 'full_screen'),
                                    background_color=config.get('screen', 'background_color'),
                                    gamma_scale=config.get('screen', 'gamma_scale'),
                                    physical_screen_distance=config.get('screen', 'physical_screen_distance'),
                                    physical_screen_size=config.get('screen', 'physical_screen_size'),
                                    max_lums=config.get('screen', 'max_lums'),
                                    wait_blanking=config.get('screen', 'wait_blanking'),
                                    screen_nr=config.get('screen', 'screen_nr'),
                                    mouse_visible=config.get('screen', 'mouse_visible'))

        self.phase_durations = np.array([-0.0001,  # wait for scan pulse
                                         -5,
                                         1,
                                         -5])  # the strings will be filled before every trial

        self.load_design()
        self.prepare_objects()
        self.prepare_staircase()

    # creating a mixture class would be a lot nicer but I can't be bothered so I'll cheat and include everything
    # here
    def setup_sound_system(self):
        """initialize pyaudio backend, and create dictionary of sounds."""
        self.pyaudio = pyaudio.PyAudio()
        self.sound_files = \
        subprocess.Popen('ls ' + os.path.join('.', 'sounds', '*.wav'), shell=True,
                         stdout=subprocess.PIPE).communicate()[0].split('\n')[0:-1]
        self.sounds = {}
        for sf in self.sound_files:
            self.read_sound_file(file_name=sf)
            # print self.sounds

    def read_sound_file(self, file_name, sound_name=None):
        """Read sound file from file_name, and append to self.sounds with name as key"""
        if sound_name == None:
            sound_name = os.path.splitext(os.path.split(file_name)[-1])[0]

        rate, data = wavfile.read(file_name)
        # create stream data assuming 2 channels, i.e. stereo data, and use np.float32 data format
        stream_data = data.astype(np.int16)

        # check data formats - is this stereo sound? If so, we need to fix it.
        wf = wave.open(file_name, 'rb')
        # print sound_name
        # print wf.getframerate(), wf.getnframes(), wf.getsampwidth(), wf.getnchannels()
        if wf.getnchannels() == 2:
            stream_data = stream_data[::2]

        self.sounds.update({sound_name: stream_data})

    def play_bleep(self):

        if self.config.get('audio', 'engine') == 'TK':
            self.play_sound('0')
        else:
            self.bleeper.play()

    def load_design(self):

        fn = 'sub-' + str(self.subject_initials).zfill(3) + '_session-' + str(self.index_number) + '_run-' + str(self.run_nr) + '-design'
        design = pd.read_csv(os.path.join('designs', fn + '.csv'), sep='\t', index_col=False)

        self.design = design
        self.design.direction = pd.to_numeric(self.design.direction)
        self.design.stop_trial = pd.to_numeric(self.design.stop_trial)
        self.design.jitter = pd.to_numeric(self.design.jitter)

    def prepare_staircase(self):
        # TODO: load from previous run?

        n_stop_trials = self.design.stop_trial.sum()

        # Make dict
        info = {'startPoints': [.050, .100, .150, .200]}  # start points for the four staircases

        # create staircases
        self.stairs = []
        for thisStart in info['startPoints']:
            # we need a COPY of the info for each staircase
            # (or the changes here will be made to all the other staircases)
            thisInfo = copy.copy(info)

            # now add any specific info for this staircase
            thisInfo['thisStart'] = thisStart  # we might want to keep track of this
            thisStair = data.StairHandler(startVal=thisStart,
                                          extraInfo=thisInfo,
                                          stepType='lin',
                                          minVal=0,
                                          nTrials=1000,
                                          maxVal=1.000,
                                          stepSizes=[0.050])
            self.stairs.append(thisStair)

        staircase_idx = np.tile([0, 1, 2, 3], reps=1000)[:n_stop_trials]
        np.random.shuffle(staircase_idx)
        self.design.staircase_ID = -1
        self.design.loc[self.design.stop_trial == 1, 'staircase_id'] = staircase_idx

    def prepare_objects(self):
        config = self.config

        self.left_stim = StopStimulus(screen=self.screen, direction=0,
                                      arrow_size_horizontal_degrees=config.get('stimulus', 'arrow_size'))
        self.right_stim = StopStimulus(screen=self.screen, direction=1,
                                       arrow_size_horizontal_degrees=config.get('stimulus', 'arrow_size'))
        self.fixation_circle = FixationCircle(screen=self.screen,
                                              circle_radius_degrees=config.get('stimulus', 'circle_radius_degrees'),
                                              line_width=config.get('stimulus', 'line_width'),
                                              line_color=config.get('stimulus', 'line_color'))

        self.scanner_wait_screen = visual.TextStim(win=self.screen,
                                                   text='Waiting for scanner...',
                                                   name='scanner_wait_screen',
                                                   units='pix', font='Helvetica Neue', pos=(0, 0),
                                                   italic=True,
                                                   height=30, alignHoriz='center')
        if self.subject_initials == 'DEBUG':
            self.stop_timing_circle = visual.Circle(win=self.screen,
                                                    radius=3, edges=50, lineWidth=1.5, fillColor='red',
                                                    lineColor='red', units='deg',
                                                    lineColorSpace='rgb', fillColorSpace='rgb')

    def run(self):
        """ Runs a block of this Stop Signal task"""

        for i in range(self.design.shape[0]):
            # prepare the parameters of the following trial based on the shuffled trial array
            this_trial_info = self.design.iloc[i]

            is_stop_trial = this_trial_info['stop_trial']
            if is_stop_trial:
                this_trial_staircase_id = int(this_trial_info['staircase_id'])
                this_trial_ssd = next(self.stairs[this_trial_staircase_id])
                this_staircase_start_val = self.stairs[this_trial_staircase_id].extraInfo['thisStart']
            else:
                this_trial_staircase_id = -1
                this_trial_ssd = -1
                this_staircase_start_val = -1

            this_trial_parameters = {'direction': this_trial_info['direction'],
                                     'stop_trial': this_trial_info['stop_trial'],
                                     'current_ssd': this_trial_ssd,
                                     'current_staircase': this_trial_staircase_id,
                                     'staircase_start_val': this_staircase_start_val}

            these_phase_durations = self.phase_durations.copy()
            these_phase_durations[1] = this_trial_info.jitter
            these_phase_durations[3] = 0  # 9 - these_phase_durations[1] - these_phase_durations[2]

            this_trial = StopSignalTrial(ID=i,
                                         parameters=this_trial_parameters,
                                         phase_durations=these_phase_durations,
                                         session=self,
                                         screen=self.screen)

            # run the prepared trial
            this_trial.run()

            # Update staircase if this was a stop trial
            if is_stop_trial:
                if this_trial.response_measured:
                    # Failed stop: Decrease SSD
                    self.stairs[this_trial_staircase_id].addData(0)
                else:
                    # Successful stop: Increase SSD
                    self.stairs[this_trial_staircase_id].addData(1)

            if self.stopped == True:
                break

        self.close()




if __name__ == '__main__':
    from psychopy import core

    # Load config
    from exptools.utils.config import ExpToolsConfig
    config = ExpToolsConfig()

    # Set-up monitor on the fly
    from psychopy import monitors
    my_monitor = monitors.Monitor(name=config.get('screen', 'monitor_name'))
    my_monitor.setSizePix(config.get('screen', 'size'))
    my_monitor.setWidth(config.get('screen', 'physical_screen_size')[0])
    my_monitor.setDistance(config.get('screen', 'physical_screen_distance'))
    my_monitor.saveMon()

    # Set-up session
    sess = StopSignalSession('DEBUG',
                             1,
                             run=1,
                             tr=3,
                             config=config)

    # EMULATOR
    from psychopy.hardware.emulator import launchScan
    scanner_emulator = launchScan(win=sess.screen, settings={'TR': .5, 'volumes': 30000, 'sync': 't'}, mode='Test')

    # run
    sess.run()

    # Load & dump data
    import cPickle as pkl
    from pprint import pprint

    with open(sess.output_file + '_outputDict.pkl', 'r') as f:
        a = pkl.load(f)
    pprint(a)

    core.quit()