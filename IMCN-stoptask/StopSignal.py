from exptools.core.session import MRISession
from StopStimulus import StopStimulus, FixationCircle
from StopTrial import StopSignalTrial, EndOfBlockTrial, TestSoundTrial
from psychopy import visual, data
import datetime
import glob
import pandas as pd
import numpy as np
import os
import pyaudio
import subprocess
import wave
from scipy.io import wavfile
import copy
import cPickle as pkl


class StopSignalSession(MRISession):

    def __init__(self, subject_initials, index_number, tr, start_block, config):
        super(StopSignalSession, self).__init__(subject_initials,
                                                index_number,
                                                tr=tr,
                                                simulate_mri_trigger=False,
                                                # NB: DO NOT use this MRI simulation option, but rather another!
                                                mri_trigger_key=config.get('mri', 'mri_trigger_key'))

        self.config = config
        self.start_block = start_block  # allows for starting at a later block than 1
        self.warmup_trs = config.get('mri', 'warmup_trs')

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

        # Try this
        # TODO: think about really including this?
        self.screen.recordFrameIntervals = True

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

        fn = 'sub-' + str(self.subject_initials).zfill(3) + '_session-' + str(self.index_number) + '_design'
        design = pd.read_csv(os.path.join('designs', fn + '.csv'), sep='\t', index_col=False)

        self.design = design
        self.design = self.design.apply(pd.to_numeric)  # cast all to numeric
#        self.design.stop_trial = pd.to_
#        print(self.design)

    def prepare_staircase(self):
        # TODO: load from previous run?

        # check for old file
        now = datetime.datetime.now()
        opfn = now.strftime("%Y-%m-%d")
        expected_filename = str(self.subject_initials) + '_' + str(self.index_number) + '_' + opfn
        fns = glob.glob('./data/' + expected_filename + '_*_staircases.pkl')

        if self.start_block > 1 and len(fns) == 1:
            # if previous run was created
            with open(fns[0], 'r') as f:
                self.stairs = pkl.load(f)
        else:
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

            # Save staircases
            with open(self.output_file + '_staircases.pkl', 'w') as f:
                pkl.dump(self.stairs, f)

        self.design.staircase_ID = -1
        for block in np.unique(self.design.block):
            if block < self.start_block:
                continue

            # how many stop trials this block?
            n_stop_trials = self.design.loc[self.design.block == block].stop_trial.sum()
            staircase_idx = np.tile([0, 1, 2, 3], reps=1000)[:n_stop_trials]
            np.random.shuffle(staircase_idx)

            # append to design
            self.design.loc[(self.design.stop_trial == 1) & (self.design.block == block), 'staircase_id'] = \
                staircase_idx

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

    def save_data(self, trial_handler=None, block_n='all'):

        output_fn_dat = self.output_file + '_block-' + str(block_n)
        output_fn_frames = self.output_file + '_block-' + str(block_n)

        if trial_handler is not None:
            trial_handler.saveAsPickle(output_fn_dat)
            trial_handler.saveAsWideText(output_fn_dat + '.csv', )

        if self.screen.recordFrameIntervals:
            # Save frame intervals to file
            self.screen.saveFrameIntervals(fileName=output_fn_frames + '_frameintervals.log', clear=False)

            # import matplotlib.pyplot as plt
            # # Make a nice figure
            # intervals_ms = np.array(self.screen.frameIntervals) * 1000
            # m = np.mean(intervals_ms)
            # sd = np.std(intervals_ms)
            #
            # msg = "Mean=%.1fms, s.d.=%.2f, 99%%CI(frame)=%.2f-%.2f"
            # dist_string = msg % (m, sd, m - 2.58 * sd, m + 2.58 * sd)
            # n_total = len(intervals_ms)
            # n_dropped = sum(intervals_ms > (1.5 * m))
            # msg = "Dropped/Frames = %i/%i = %.3f%%"
            # dropped_string = msg % (n_dropped, n_total, 100 * n_dropped / float(n_total))
            #
            # # plot the frame intervals
            # plt.figure(figsize=[12, 8])
            # plt.subplot(1, 2, 1)
            # plt.plot(intervals_ms, '-')
            # plt.ylabel('t (ms)')
            # plt.xlabel('frame N')
            # plt.title(dropped_string)
            #
            # plt.subplot(1, 2, 2)
            # plt.hist(intervals_ms, 50, normed=0, histtype='stepfilled')
            # plt.xlabel('t (ms)')
            # plt.ylabel('n frames')
            # plt.title(dist_string)
            # plt.savefig(output_fn_frames + '_frameintervals.png')

    def close(self):
        """ Saves stuff and closes """

        self.save_data()
        super(StopSignalSession, self).close()


    def run(self):
        """ Runs this Stop Signal task"""

        test_sound = TestSoundTrial(ID=-1, parameters={}, phase_durations=[1000], session=self, screen=self.screen,
                                    tracker=None)
        test_sound.run()
        self.block_start_time = 0

        for block_n in np.unique(self.design.block):
            if block_n < self.start_block:
                continue
            this_block_design = self.design.loc[self.design.block == block_n]

            trial_handler = data.TrialHandler(this_block_design.to_dict('records'),
                                              nReps=1,
                                              method='sequential')

            for block_trial_ID, this_trial_info in enumerate(trial_handler):

                is_stop_trial = this_trial_info['stop_trial']
                if is_stop_trial:
                    this_trial_staircase_id = int(this_trial_info['staircase_id'])
                    this_trial_ssd = next(self.stairs[this_trial_staircase_id])
                    this_staircase_start_val = self.stairs[this_trial_staircase_id].extraInfo['thisStart']
                else:
                    this_trial_staircase_id = -1
                    this_trial_ssd = -1
                    this_staircase_start_val = -1

                this_trial_parameters = {'direction': int(this_trial_info['direction']),
                                         'stop_trial': int(this_trial_info['stop_trial']),
                                         'current_ssd': this_trial_ssd,
                                         'current_staircase': this_trial_staircase_id,
                                         'staircase_start_val': this_staircase_start_val,
                                         'block': block_n,
                                         'block_trial_ID': block_trial_ID}

                these_phase_durations = self.phase_durations.copy()
                these_phase_durations[1] = this_trial_info.jitter
                # NB we stop the trial 0.5s before the start of the new trial, to allow sufficient computation time
                # for preparing the next trial. Therefore 8.5s instead of 9s.
                these_phase_durations[3] = 8.5 - these_phase_durations[1] - these_phase_durations[2]

                this_trial = StopSignalTrial(ID=int(this_trial_info.trial_ID),
                                             parameters=this_trial_parameters,
                                             phase_durations=these_phase_durations,
                                             session=self,
                                             screen=self.screen)

                # run the prepared trial
                this_trial.run()

                # Record some stuff
                trial_handler.addData('rt', this_trial.rt)
                trial_handler.addData('response', this_trial.response)

                # absolute times since session start
                trial_handler.addData('start_time', this_trial.start_time)
                trial_handler.addData('t_time', this_trial.t_time)
                trial_handler.addData('jitter_time', this_trial.jitter_time)
                trial_handler.addData('stimulus_time', this_trial.stimulus_time)
                trial_handler.addData('iti_time', this_trial.iti_time)

                # durations / time since actual trial start (note that the *actual* trial start is t_time!)
                if is_stop_trial:
                    trial_handler.addData('ssd', this_trial_ssd)
                    trial_handler.addData('stop_signal_time_recorded', this_trial.bleep_time - this_trial.jitter_time)
                    trial_handler.addData('staircase_start_val', this_staircase_start_val)

                trial_handler.addData('phase_0_measured', this_trial.t_time - this_trial.start_time)
                trial_handler.addData('phase_1_measured', this_trial.jitter_time - this_trial.t_time)
                trial_handler.addData('phase_2_measured', this_trial.stimulus_time - this_trial.jitter_time)
                trial_handler.addData('phase_3_measured', this_trial.iti_time - this_trial.stimulus_time)

                # durations / time since actual start of the block. These are useful to create events-files later for
                #  convolving. Can also grab these from the eventArray though.
                trial_handler.addData('trial_t_time_block_measured', this_trial.t_time - self.block_start_time)
                trial_handler.addData('stimulus_onset_time_block_measured', this_trial.jitter_time -
                                      self.block_start_time)
                # Counter-intuitive, but jitter_time is END of the jitter period = onset of stim

                # Update staircase if this was a stop trial
                if is_stop_trial:
                    if this_trial.response_measured:
                        # Failed stop: Decrease SSD
                        self.stairs[this_trial_staircase_id].addData(1)
                    else:
                        # Successful stop: Increase SSD
                        self.stairs[this_trial_staircase_id].addData(0)

                if self.stopped:
                    # out of trial
                    break

            # Save
            self.save_data(trial_handler, block_n)

            if self.stopped:
                # out of block
                break


            # end of block
            this_trial = EndOfBlockTrial(ID=int('999' + str(block_n)),
                                         parameters={},
                                         phase_durations=[1000],
                                         session=self,
                                         screen=self.screen)
            this_trial.run()

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
    scanner_emulator = launchScan(win=sess.screen, settings={'TR': 3, 'volumes': 30000, 'sync': 't'}, mode='Test')

    # run
    sess.run()

    # Load & dump data
    import cPickle as pkl
    from pprint import pprint

    with open(sess.output_file + '_outputDict.pkl', 'r') as f:
        a = pkl.load(f)
    pprint(a)

    core.quit()