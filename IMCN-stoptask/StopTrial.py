from exptools.core.trial import MRITrial
from exptools.core.session import MRISession
from psychopy import event

class StopSignalTrial(MRITrial):

    def __init__(self, ID, parameters, phase_durations, session=None, screen=None, tracker=None):
        super(StopSignalTrial, self).__init__(parameters=parameters,
                                              phase_durations=phase_durations,
                                              session=session,
                                              screen=screen,
                                              tracker=tracker)

        self.ID = ID
        self.has_bleeped = False
        self.response_measured = False  # Has the pp responded yet?

        if parameters['direction'] == 0:
            self.stim = self.session.left_stim
        else:
            self.stim = self.session.right_stim

        if parameters['stop_trial'] == 1:
            self.stop_trial = True
        else:
            self.stop_trial = False

        self.parameters = parameters

        # initialize times
        self.t_time = self.jitter_time = self.stimulus_time = self.iti_time = None

    def event(self):

        for ev, time in event.getKeys(timeStamped=self.session.clock):
            if len(ev) > 0:
                if ev in ['esc', 'escape']:
                    self.events.append([-99, time, self.session.clock.getTime() - self.start_time])
                    self.stopped = True
                    self.session.stopped = True
                    print 'run canceled by user'

                # it handles both numeric and lettering modes
                elif ev == '+':
                    self.events.append([-99, time, self.session.clock.getTime() - self.start_time])
                    self.stopped = True
                    print 'trial canceled by user'

                elif ev == self.session.mri_trigger_key:  # TR pulse
                    self.events.append([99, time, self.session.clock.getTime() - self.start_time])
                    # phase 0 is ended by the MR trigger
                    if self.phase == 0:
                        self.phase_forward()

                elif ev in self.session.response_button_signs:
                    self.events.append([ev, time, self.session.clock.getTime() - self.start_time, 'key_press'])

                    if self.phase == 2:
                        self.response_measured = True

            super(StopSignalTrial, self).key_event(ev)

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

            # Waits for scanner pulse. If first
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
                        print('this is a stop trial, beeping now!')
                        self.session.play_bleep()
                        self.has_bleeped = True
                        print('I bleeped. Hooray')

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
            if self.ID == 0:
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
