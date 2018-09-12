from exptools.core.trial import MRITrial
from exptools.core.session import MRISession
from psychopy import event, visual

class StopSignalTrial(MRITrial):

    def __init__(self, ID, parameters, phase_durations, session=None, screen=None, tracker=None):
        super(StopSignalTrial, self).__init__(parameters=parameters,
                                              phase_durations=phase_durations,
                                              session=session,
                                              screen=screen,
                                              tracker=tracker)
        self.trs_recorded = 0
        self.ID = ID
        self.has_bleeped = False
        self.response_measured = False  # Has the pp responded yet?
        self.response = None
        self.rt = -1
        self.bleep_time = -1

        if bool(parameters['direction']):
            self.stim = self.session.left_stim
        else:
            self.stim = self.session.right_stim

        if bool(parameters['stop_trial']):
            self.stop_trial = True
        else:
            self.stop_trial = False

        self.parameters = parameters

        # initialize times
        self.t_time = self.jitter_time = self.stimulus_time = self.iti_time = -1

    def event(self):

        for ev, time in event.getKeys(timeStamped=self.session.clock):
            if len(ev) > 0:
                if ev in ['esc', 'escape']:
                    self.events.append([-99, time, self.session.clock.getTime() - self.start_time])
                    self.stopped = True
                    self.session.stopped = True
                    print 'run canceled by user'

                # it handles both numeric and lettering modes
                elif ev == '+' or ev == 'equal':
                    self.events.append([-99, time, self.session.clock.getTime() - self.start_time])
                    self.stopped = True
                    print 'trial canceled by user'

                elif ev == self.session.mri_trigger_key:  # TR pulse
                    self.trs_recorded += 1
                    if self.phase == 0:
                        if self.trs_recorded >= self.session.warmup_trs:
                            if self.parameters['block_trial_ID'] == 0:
                                # make sure to register this pulse now as the start of the block/run
                                self.session.block_start_time = time

                    self.events.append([99,
                                        time,  # absolute time since session start
                                        time - self.start_time,  # time since trial start
                                        time - self.session.block_start_time,  # time since block start
                                        self.ID])  # trial ID seems useful maybe

                    # phase 0 is ended by the MR trigger
                    if self.phase == 0:
                        if self.parameters['block_trial_ID'] == 0:
                            if self.trs_recorded >= self.session.warmup_trs:
                                self.phase_forward()
                        else:
                            self.phase_forward()

                elif ev in self.session.response_button_signs:
                    self.events.append([ev, time,  # absolute time since start of experiment
                                        self.session.clock.getTime() - self.start_time,  # time since start of trial
                                        self.stimulus_time - self.jitter_time,  # time since stimulus start
                                        'key_press'])

                    if self.phase == 2:
                        if not self.response_measured:
                            self.response = ev
                            self.rt = self.stimulus_time - self.jitter_time  # this is RT, since self.stimulus_time is 'now'
                            self.response_measured = True

            super(StopSignalTrial, self).key_event(ev)

    def run(self):
        """
        Runs this trial
        """

        self.start_time = self.session.clock.getTime()
        if self.tracker:
            self.tracker.log('trial ' + str(self.ID) + ' started at ' + str(self.start_time))
            self.tracker.send_command('record_status_message "Trial ' + str(self.ID) + '"')
        self.events.append('trial ' + str(self.ID) + ' started at ' + str(self.start_time))

        while not self.stopped:
            self.run_time = self.session.clock.getTime() - self.start_time

            # Waits for scanner pulse.
            if self.phase == 0:
                self.t_time = self.session.clock.getTime()
                if not isinstance(self.session, MRISession):
                    self.phase_forward()

            # In phase 1, we show fix cross (jittered timing)
            if self.phase == 1:
                self.jitter_time = self.session.clock.getTime()
                if (self.jitter_time - self.t_time) > self.phase_durations[1]:
                    self.phase_forward()

            # In phase 2, we show the stimulus
            if self.phase == 2:
                self.stimulus_time = self.session.clock.getTime()
                if (self.stimulus_time - self.jitter_time) > self.phase_durations[2]:
                    self.phase_forward()

                if self.stop_trial and not self.has_bleeped:
                    if (self.stimulus_time - self.jitter_time) > self.parameters['current_ssd']:
                        self.bleep_time = self.session.clock.getTime()  # ABSOLUTE bleep time
                        self.session.play_bleep()
                        self.key_event('s')
                        self.events.append([5,
                                            self.session.clock.getTime(),  # absolute time since start of exp
                                            self.stimulus_time - self.jitter_time,  # time of sound relative to
                                            # stimulus start
                                            self.session.clock.getTime() - self.start_time,  # time of sound relative
                                            #  to start of trial
                                            'bleep'])
                        self.has_bleeped = True

            # In phase 3, we show the fix cross again (iti)
            if self.phase == 3:
                self.iti_time = self.session.clock.getTime()
                if (self.iti_time - self.stimulus_time) > self.phase_durations[3]:
                    self.phase_forward()
                    self.stopped = True

            # events and draw, but only if we haven't stopped yet
            if not self.stopped:
                self.event()
                self.draw()

        self.stop()

    def draw(self):

        if self.phase == 0:   # waiting for scanner-time
            if self.parameters['block_trial_ID'] == 0:
                self.session.scanner_wait_screen.draw()
#            else:
#                self.session.fixation_circle.draw()
        elif self.phase == 1:  # Pre-cue fix cross
            self.session.fixation_circle.draw()

        elif self.phase == 2:  # Stimulus
            self.session.fixation_circle.draw()
            self.stim.draw()
            # if not os.path.isfile('screenshot_localizer_cue_' + str(self.correct_answer) + '.png'):
            #     self.session.screen.flip()
            #     self.session.screen.getMovieFrame()
            #     self.session.screen.saveMovieFrames('screenshot_localizer_cue_' + str(self.correct_answer) + '.png')

            if self.session.subject_initials == 'DEBUG':
                if self.stop_trial:
                    if (self.stimulus_time - self.jitter_time) > self.parameters['current_ssd']:
                        self.session.stop_timing_circle.draw()

        # elif self.phase == 3:  # Post-stimulus
        #     self.session.fixation_circle.draw()

        super(StopSignalTrial, self).draw()


class EndOfBlockTrial(MRITrial):

    def __init__(self, ID, parameters, phase_durations, session=None, screen=None, tracker=None):
        super(EndOfBlockTrial, self).__init__(parameters=parameters,
                                              phase_durations=phase_durations,
                                              session=session,
                                              screen=screen,
                                              tracker=tracker)

        self.ID = ID
        self.parameters = parameters

        # initialize times
        self.t_time = self.jitter_time = self.stimulus_time = self.iti_time = None

        self.instruction_text = visual.TextStim(screen, text='End of block. Waiting for operator...')

    def event(self):

        for ev, time in event.getKeys(timeStamped=self.session.clock):
            if len(ev) > 0:
                if ev in ['esc', 'escape']:
                    self.events.append([-99, time, self.session.clock.getTime() - self.start_time])
                    self.stopped = True
                    self.session.stopped = True
                    print 'run canceled by user'

                # it handles both numeric and lettering modes
                elif ev == '+' or ev == 'equal':
                    self.events.append([-99, time, self.session.clock.getTime() - self.start_time])
                    self.stopped = True
                    print 'trial canceled by user'

                elif ev == self.session.mri_trigger_key:  # TR pulse
                    self.events.append([99, time, self.session.clock.getTime() - self.start_time])

                elif ev in self.session.response_button_signs:
                    self.events.append([ev, time, self.session.clock.getTime() - self.start_time, 'key_press'])

            super(EndOfBlockTrial, self).key_event(ev)

    def run(self):
        """
        Runs this trial
        """

        self.start_time = self.session.clock.getTime()
        if self.tracker:
            self.tracker.log('trial ' + str(self.ID) + ' started at ' + str(self.start_time) )
            self.tracker.send_command('record_status_message "Trial ' + str(self.ID) + '"')
        self.events.append('trial ' + str(self.ID) + ' started at ' + str(self.start_time))

        while not self.stopped:
            self.run_time = self.session.clock.getTime() - self.start_time

            # waits for operator to press '+'
            if self.phase == 0:
                self.t_time = self.session.clock.getTime()

            # events and draw, but only if we haven't stopped yet
            if not self.stopped:
                self.event()
                self.draw()

        self.stop()

    def draw(self):

        if self.phase == 0:   # waiting for scanner-time
            self.instruction_text.draw()

        super(EndOfBlockTrial, self).draw()



class TestSoundTrial(MRITrial):

    def __init__(self, ID, parameters, phase_durations, session=None, screen=None, tracker=None):
        super(TestSoundTrial, self).__init__(parameters=parameters,
                                              phase_durations=phase_durations,
                                              session=session,
                                              screen=screen,
                                              tracker=tracker)

        self.ID = ID
        self.parameters = parameters

        # initialize times
        self.t_time = self.jitter_time = self.stimulus_time = self.iti_time = None

        self.instruction_text = visual.TextStim(screen, text='Testing sound...')

    def event(self):

        for ev, time in event.getKeys(timeStamped=self.session.clock):
            if len(ev) > 0:
                if ev in ['esc', 'escape']:
                    self.events.append([-99, time, self.session.clock.getTime() - self.start_time])
                    self.stopped = True
                    self.session.stopped = True
                    print 'run canceled by user'

                # it handles both numeric and lettering modes
                elif ev == '+' or ev == 'equal':
                    self.events.append([-99, time, self.session.clock.getTime() - self.start_time])
                    self.stopped = True
                    print 'trial canceled by user'

                elif ev == self.session.mri_trigger_key:  # TR pulse
                    self.events.append([99, time, self.session.clock.getTime() - self.start_time, self.ID])

                elif ev in self.session.response_button_signs:
                    self.events.append([2, time, self.session.clock.getTime() - self.start_time, ev, 'key_press'])

                elif ev in ['s']:
                    self.session.play_bleep()

            super(TestSoundTrial, self).key_event(ev)

    def run(self):
        """
        Runs this trial
        """

        self.start_time = self.session.clock.getTime()
        if self.tracker:
            self.tracker.log('trial ' + str(self.ID) + ' started at ' + str(self.start_time) )
            self.tracker.send_command('record_status_message "Trial ' + str(self.ID) + '"')
        self.events.append('trial ' + str(self.ID) + ' started at ' + str(self.start_time))

        while not self.stopped:
            self.run_time = self.session.clock.getTime() - self.start_time

            # waits for operator to press '+'
            if self.phase == 0:
                self.t_time = self.session.clock.getTime()

            # events and draw, but only if we haven't stopped yet
            if not self.stopped:
                self.event()
                self.draw()

        self.stop()

    def draw(self):

        if self.phase == 0:   # waiting for scanner-time
            self.instruction_text.draw()

        super(TestSoundTrial, self).draw()